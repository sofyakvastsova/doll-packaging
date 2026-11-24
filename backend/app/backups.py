import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from app.db.database import BACKEND_ROOT, DATABASE_PATH
from app.storage.local import DEFAULT_STORAGE_ROOT, LocalFileStorage

LEGACY_UPLOAD_ROOT = BACKEND_ROOT / 'uploads' / 'images'
_configured_backup_root = Path(os.getenv(
    'BACKUP_ROOT',
    str(Path.home() / 'Library' / 'Application Support' / 'DollPackaging' / 'backups'),
)).expanduser()
DEFAULT_BACKUP_ROOT = (
    (BACKEND_ROOT / _configured_backup_root).resolve()
    if not _configured_backup_root.is_absolute()
    else _configured_backup_root.resolve()
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_name(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe archive path: {name}')


def verify_backup(archive_path: Path | str) -> dict:
    archive_path = Path(archive_path).expanduser().resolve()
    with zipfile.ZipFile(archive_path, 'r') as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f'Corrupt ZIP member: {bad_member}')
        names = archive.namelist()
        for name in names:
            _zip_name(name)
        if 'manifest.json' not in names or 'database/projects.sqlite3' not in names:
            raise ValueError('Backup is missing its manifest or SQLite database.')
        manifest = json.loads(archive.read('manifest.json'))
        expected = manifest.get('files')
        if not isinstance(expected, dict):
            raise ValueError('Backup manifest is invalid.')
        for name, digest in expected.items():
            _zip_name(name)
            if name not in names or _sha256(archive.read(name)) != digest:
                raise ValueError(f'Backup file failed SHA-256 verification: {name}')
        if set(expected) != set(names) - {'manifest.json'}:
            raise ValueError('Backup archive contains unlisted files.')

        with tempfile.TemporaryDirectory(prefix='doll-db-verify-') as temporary:
            db_path = Path(temporary) / 'projects.sqlite3'
            db_path.write_bytes(archive.read('database/projects.sqlite3'))
            connection = sqlite3.connect(db_path)
            try:
                integrity = connection.execute('PRAGMA integrity_check').fetchone()[0]
                if integrity != 'ok':
                    raise ValueError(f'SQLite integrity check failed: {integrity}')
                foreign_key_errors = connection.execute('PRAGMA foreign_key_check').fetchall()
                if foreign_key_errors:
                    raise ValueError(f'SQLite foreign key check failed: {foreign_key_errors[:5]}')
                if 'assets' in {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
                    for (storage_key,) in connection.execute('SELECT storage_key FROM assets'):
                        _zip_name(f'storage/{storage_key}')
                        if f'storage/{storage_key}' not in expected:
                            raise ValueError(f'Backup is missing project asset: {storage_key}')
            finally:
                connection.close()
    return manifest


def create_backup(
    backup_root: Path | str = DEFAULT_BACKUP_ROOT,
    *,
    database_path: Path | str = DATABASE_PATH,
    storage_root: Path | str = DEFAULT_STORAGE_ROOT,
    legacy_upload_root: Path | str = LEGACY_UPLOAD_ROOT,
) -> Path:
    backup_root = Path(backup_root).expanduser().resolve()
    database_path = Path(database_path).expanduser().resolve()
    storage = LocalFileStorage(storage_root)
    legacy_upload_root = Path(legacy_upload_root).expanduser().resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f'SQLite database does not exist: {database_path}')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    final_path = backup_root / f'doll-packaging-{timestamp}.zip'
    temporary_path = backup_root / f'.{final_path.stem}-{uuid.uuid4().hex}.tmp'
    try:
        temporary_fd = os.open(temporary_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(temporary_fd)
        with storage.exclusive_lock():
            with tempfile.TemporaryDirectory(prefix='doll-db-backup-') as temporary:
                snapshot_path = Path(temporary) / 'projects.sqlite3'
                source = sqlite3.connect(f'file:{database_path}?mode=ro', uri=True, timeout=30)
                destination = sqlite3.connect(snapshot_path)
                try:
                    source.backup(destination, pages=256, sleep=0.05)
                    integrity = destination.execute('PRAGMA integrity_check').fetchone()[0]
                    if integrity != 'ok':
                        raise ValueError(f'Source database failed integrity check: {integrity}')
                    if destination.execute('PRAGMA foreign_key_check').fetchone() is not None:
                        raise ValueError('Source database has foreign key violations.')
                finally:
                    destination.close()
                    source.close()

                hashes: dict[str, str] = {}
                with zipfile.ZipFile(temporary_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                    db_bytes = snapshot_path.read_bytes()
                    archive.writestr('database/projects.sqlite3', db_bytes)
                    hashes['database/projects.sqlite3'] = _sha256(db_bytes)
                    for root, prefix in ((storage.root / 'projects', 'storage/projects'), (legacy_upload_root, 'legacy_uploads')):
                        if not root.is_dir():
                            continue
                        for file_path in sorted(root.rglob('*')):
                            if not file_path.is_file() or file_path.is_symlink() or file_path.name == '.backup.lock':
                                continue
                            relative = file_path.relative_to(root).as_posix()
                            name = f'{prefix}/{relative}'
                            _zip_name(name)
                            content = file_path.read_bytes()
                            archive.writestr(name, content)
                            hashes[name] = _sha256(content)
                    manifest = {
                        'format_version': 1,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'sqlite_version': sqlite3.sqlite_version,
                        'legacy_uploads_included': legacy_upload_root.is_dir(),
                        'files': hashes,
                    }
                    archive.writestr('manifest.json', json.dumps(manifest, indent=2, sort_keys=True).encode())
        verify_backup(temporary_path)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, final_path)
        directory_fd = os.open(backup_root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return final_path
    finally:
        temporary_path.unlink(missing_ok=True)


def verified_backups(backup_root: Path | str) -> list[tuple[Path, dict]]:
    root = Path(backup_root).expanduser().resolve()
    if not root.is_dir():
        return []
    valid: list[tuple[Path, dict]] = []
    for path in root.glob('doll-packaging-*.zip'):
        try:
            valid.append((path, verify_backup(path)))
        except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
            print(f'WARNING: keeping invalid backup {path.name}: {error}')
    return sorted(valid, key=lambda item: item[1]['created_at'], reverse=True)