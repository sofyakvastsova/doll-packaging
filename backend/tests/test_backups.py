import json
import sqlite3
import sys
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from app import backups
from app.db import database
from app.storage.local import LocalFileStorage
import retention
from retention import retained_paths


def test_backup_contains_consistent_database_and_project_files(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'source.sqlite3')
    database.initialize_database()
    project, _token = database.create_project('bratz')
    storage_root = tmp_path / 'storage'
    storage = LocalFileStorage(storage_root)
    key = storage.save(project['id'], 'original_photo', b'\x89PNG\r\n\x1a\nphoto', 'image/png')
    database.add_asset(project['id'], 'original_photo', key, 'image/png', 13)
    legacy_root = tmp_path / 'legacy'
    legacy_root.mkdir()
    (legacy_root / 'legacy-image.png').write_bytes(b'legacy')

    backup_path = backups.create_backup(
        tmp_path / 'backups',
        database_path=database.DATABASE_PATH,
        storage_root=storage_root,
        legacy_upload_root=legacy_root,
    )
    manifest = backups.verify_backup(backup_path)
    assert 'database/projects.sqlite3' in manifest['files']
    assert f'storage/projects/{key.removeprefix("projects/")}' in manifest['files']
    assert 'legacy_uploads/legacy-image.png' in manifest['files']

    with zipfile.ZipFile(backup_path) as archive:
        assert archive.read(f'storage/{key}') == b'\x89PNG\r\n\x1a\nphoto'
        assert archive.read('legacy_uploads/legacy-image.png') == b'legacy'
        db_bytes = archive.read('database/projects.sqlite3')
        (tmp_path / 'restored.sqlite3').write_bytes(db_bytes)
    restored = sqlite3.connect(tmp_path / 'restored.sqlite3')
    try:
        assert restored.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 1
        assert restored.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        restored.close()


def test_backup_verification_detects_tampered_content(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'source.sqlite3')
    database.initialize_database()
    backup_path = backups.create_backup(
        tmp_path / 'backups', database_path=database.DATABASE_PATH,
        storage_root=tmp_path / 'storage', legacy_upload_root=tmp_path / 'legacy',
    )
    with zipfile.ZipFile(backup_path) as source:
        members = {name: source.read(name) for name in source.namelist()}
    members['database/projects.sqlite3'] += b'tampered'
    with zipfile.ZipFile(backup_path, 'w') as altered:
        for name, content in members.items():
            altered.writestr(name, content)
    with pytest.raises(ValueError, match='SHA-256'):
        backups.verify_backup(backup_path)


def test_retention_selects_newest_backups_and_gfs_buckets(tmp_path):
    origin = datetime(2026, 11, 18, tzinfo=timezone.utc)
    backups_list = []
    for day in range(75):
        created = origin - timedelta(days=day)
        path = tmp_path / f'{day}.zip'
        backups_list.append((path, {'created_at': created.isoformat()}))
    assert len(retained_paths(backups_list, keep=7)) == 7
    gfs = retained_paths(backups_list, keep_daily=7, keep_weekly=4, keep_monthly=3)
    assert backups_list[0][0] in gfs
    assert len(gfs) >= 7


def test_retention_requires_at_least_one_backup():
    with pytest.raises(ValueError):
        retained_paths([], keep=0)


def test_retention_dry_run_never_deletes_or_creates(tmp_path, monkeypatch, capsys):
    old = tmp_path / 'old.zip'
    new = tmp_path / 'new.zip'
    old.touch()
    new.touch()
    created = []
    monkeypatch.setattr(sys, 'argv', ['retention.py', str(tmp_path), '--keep', '1'])
    monkeypatch.setattr(retention, 'create_backup', lambda _root: created.append(True))
    monkeypatch.setattr(retention, 'verified_backups', lambda _root: [
        (new, {'created_at': '2026-01-02T00:00:00+00:00'}),
        (old, {'created_at': '2026-01-01T00:00:00+00:00'}),
    ])
    assert retention.main() == 0
    assert old.exists()
    assert new.exists()
    assert created == []
    assert 'Would remove' in capsys.readouterr().out


def test_retention_apply_verifies_fresh_copy_before_pruning(tmp_path, monkeypatch):
    old = tmp_path / 'old.zip'
    old.touch()
    fresh = tmp_path / 'fresh.zip'
    events = []

    def create(_root):
        events.append('create-and-verify')
        fresh.touch()
        return fresh

    def list_verified(_root):
        events.append('list-verified')
        return [(fresh, {'created_at': '2026-01-02T00:00:00+00:00'}),
                (old, {'created_at': '2026-01-01T00:00:00+00:00'})]

    monkeypatch.setattr(sys, 'argv', ['retention.py', str(tmp_path), '--keep', '1', '--apply'])
    monkeypatch.setattr(retention, 'create_backup', create)
    monkeypatch.setattr(retention, 'verified_backups', list_verified)
    assert retention.main() == 0
    assert events == ['create-and-verify', 'list-verified']
    assert fresh.exists()
    assert not old.exists()