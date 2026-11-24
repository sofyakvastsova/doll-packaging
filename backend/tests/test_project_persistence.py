import sqlite3

import pytest
from fastapi import HTTPException

from app.db import database
from app.storage.local import LocalFileStorage


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'projects.sqlite3')
    database.initialize_database()
    return tmp_path


def test_project_settings_assets_and_task_lifecycle(test_database):
    project, token = database.create_project('bratz', 'Sofya', {'dollName': 'Sofya'})
    assert database.authorize_project(project['id'], token)['id'] == project['id']
    assert database.authorize_project(project['id'], 'wrong-token') is None
    assert project['template_id']

    storage = LocalFileStorage(test_database / 'storage')
    content = b'\x89PNG\r\n\x1a\nproject-image'
    storage_key = storage.save(project['id'], 'original_photo', content, 'image/png')
    asset = database.add_asset(project['id'], 'original_photo', storage_key, 'image/png', len(content))
    task = database.create_task(project['id'], 'doll_generation', input_asset_id=asset['id'], provider='photopanda')
    database.finish_task(task['id'], status='succeeded', output_asset_id=asset['id'])
    database.update_project(project['id'], settings={'dollName': 'Updated'})

    snapshot = database.project_snapshot(project['id'])
    assert snapshot['settings'] == {'dollName': 'Updated'}
    assert snapshot['template_id'] == project['template_id']
    assert snapshot['status'] == 'ready'
    assert snapshot['assets'][0]['url'].endswith(f"/assets/{asset['id']}/content")
    assert snapshot['tasks'][0]['status'] == 'succeeded'
    assert storage.read(storage_key) == content

    changed = database.update_project(project['id'], style='monster_high')
    with database.connect() as connection:
        template = connection.execute('SELECT style FROM packaging_templates WHERE id=?', (changed['template_id'],)).fetchone()
    assert changed['style'] == template['style'] == 'monster_high'


def test_foreign_keys_and_project_cascade(test_database):
    project, _ = database.create_project('monster_high')
    with database.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO assets(id, project_id, asset_type, storage_key, mime_type, size_bytes, created_at) VALUES ('bad', 'missing', 'original_photo', 'projects/missing/x.png', 'image/png', 1, 'now')"
            )
    database.create_task(project['id'], 'pdf_export')
    database.delete_project(project['id'])
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM generation_tasks WHERE project_id=?', (project['id'],)).fetchone()[0] == 0


def test_local_storage_validates_project_and_key(tmp_path):
    storage = LocalFileStorage(tmp_path / 'storage')
    with pytest.raises(HTTPException):
        storage.save('not-a-project', 'original_photo', b'image', 'image/png')
    with pytest.raises(HTTPException):
        storage.save('123e4567-e89b-12d3-a456-426614174000', 'original_photo', b'image', 'text/plain')
    with pytest.raises(HTTPException):
        storage.read('../outside')
    with pytest.raises(HTTPException):
        storage.delete('/tmp/outside')


def test_local_storage_uses_random_safe_paths_and_delete(tmp_path):
    storage = LocalFileStorage(tmp_path / 'storage')
    project_id = '123e4567-e89b-12d3-a456-426614174000'
    first = storage.save(project_id, 'original_photo', b'\x89PNG\r\n\x1a\nfoo', 'image/png')
    second = storage.save(project_id, 'original_photo', b'\x89PNG\r\n\x1a\nfoo', 'image/png')
    assert first != second
    assert first.startswith(f'projects/{project_id}/originals/')
    storage.delete(first)
    with pytest.raises(FileNotFoundError):
        storage.read(first)


def test_failed_migration_rolls_back_schema_and_version(test_database, monkeypatch):
    monkeypatch.setattr(database, 'MIGRATIONS', [
        *database.MIGRATIONS,
        'CREATE TABLE partial_table(id INTEGER); INSERT INTO missing_table VALUES (1);',
    ])
    with pytest.raises(sqlite3.OperationalError):
        database.initialize_database()
    with database.connect() as connection:
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='partial_table'").fetchone() is None
        assert connection.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] == 2