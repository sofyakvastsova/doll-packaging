import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / '.env', override=False)


def _configured_path(value: str, default: Path) -> Path:
    configured = Path(value).expanduser() if value else default
    return (BACKEND_ROOT / configured).resolve() if not configured.is_absolute() else configured.resolve()


DATABASE_PATH = _configured_path(os.getenv('DATABASE_PATH', ''), BACKEND_ROOT / 'data' / 'projects.sqlite3')

MIGRATIONS = [
    '''
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        created_at TEXT NOT NULL
    );
    CREATE TABLE projects (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
        guest_token_hash TEXT NOT NULL,
        name TEXT NOT NULL DEFAULT 'Новый проект',
        style TEXT NOT NULL CHECK (style IN ('bratz', 'monster_high')),
        settings_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'ready', 'error')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX idx_projects_user_updated ON projects(user_id, updated_at);
    CREATE TABLE assets (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        asset_type TEXT NOT NULL CHECK (asset_type IN ('original_photo', 'generated_doll', 'transparent_doll', 'logo', 'packaging_preview', 'pdf', 'intermediate')),
        storage_key TEXT NOT NULL UNIQUE,
        mime_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    );
    CREATE INDEX idx_assets_project_type ON assets(project_id, asset_type, created_at);
    CREATE TABLE generation_tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        task_type TEXT NOT NULL CHECK (task_type IN ('doll_generation', 'background_removal', 'packaging_assembly', 'pdf_export')),
        status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
        input_asset_id TEXT REFERENCES assets(id) ON DELETE SET NULL,
        output_asset_id TEXT REFERENCES assets(id) ON DELETE SET NULL,
        provider TEXT,
        parameters_json TEXT NOT NULL DEFAULT '{}',
        attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
        error_message TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    );
    CREATE INDEX idx_tasks_project_created ON generation_tasks(project_id, created_at);
    CREATE TABLE packaging_templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        style TEXT NOT NULL CHECK (style IN ('bratz', 'monster_high')),
        template_path TEXT NOT NULL,
        placement_json TEXT NOT NULL DEFAULT '{}',
        version TEXT NOT NULL DEFAULT '1',
        available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
        created_at TEXT NOT NULL,
        UNIQUE(style, name, version)
    );
    ''',
    '''
    ALTER TABLE projects ADD COLUMN template_id TEXT REFERENCES packaging_templates(id) ON DELETE SET NULL;
    CREATE INDEX idx_projects_template ON projects(template_id);
    ''',
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA journal_mode = WAL')
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
        applied = {row['version'] for row in connection.execute('SELECT version FROM schema_migrations')}
        for version, migration in enumerate(MIGRATIONS, start=1):
            if version in applied:
                continue
            connection.execute('BEGIN IMMEDIATE')
            try:
                _execute_migration(connection, migration)
                connection.execute('INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)', (version, utc_now()))
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        _seed_templates(connection)


def _execute_migration(connection: sqlite3.Connection, script: str) -> None:
    statement = ''
    for character in script:
        statement += character
        if character == ';' and sqlite3.complete_statement(statement):
            sql = statement.strip()
            if sql:
                connection.execute(sql)
            statement = ''
    if statement.strip():
        raise sqlite3.OperationalError('Migration contains an incomplete SQL statement.')


def _seed_templates(connection: sqlite3.Connection) -> None:
    project_root = BACKEND_ROOT.parent
    templates = (
        ('Bratz A4 sheets', 'bratz', str(project_root / 'templates' / 'bratz'), '{}'),
        ('Monster High A4 sheets', 'monster_high', str(project_root / 'templates' / 'monster-high'),
         json.dumps({'doll': {'sheet': 2, 'left': 45, 'top': 29, 'width': 46, 'height': 48}})),
    )
    for name, style, path, placement in templates:
        connection.execute(
            '''INSERT OR IGNORE INTO packaging_templates
               (id, name, style, template_path, placement_json, version, created_at)
               VALUES (?, ?, ?, ?, ?, '1', ?)''',
            (str(uuid.uuid5(uuid.NAMESPACE_URL, f'doll-packaging:{style}:{name}')), name, style, path, placement, utc_now()),
        )
    connection.execute(
        '''UPDATE projects SET template_id = (
               SELECT id FROM packaging_templates
               WHERE packaging_templates.style = projects.style AND available = 1
               ORDER BY version DESC LIMIT 1
           ) WHERE template_id IS NULL'''
    )


def create_project(style: str, name: str = 'Новый проект', settings: dict | None = None) -> tuple[dict, str]:
    project_id = str(uuid.uuid4())
    guest_token = secrets.token_urlsafe(32)
    import hashlib

    now = utc_now()
    with connect() as connection:
        connection.execute(
                '''INSERT INTO projects(id, guest_token_hash, name, style, settings_json, created_at, updated_at, template_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, (SELECT id FROM packaging_templates WHERE style=? AND available=1 ORDER BY version DESC LIMIT 1))''',
                (project_id, hashlib.sha256(guest_token.encode()).hexdigest(), name[:200], style,
                 json.dumps(settings or {}, separators=(',', ':')), now, now, style),
        )
        row = connection.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    return dict(row), guest_token


def authorize_project(project_id: str, guest_token: str) -> sqlite3.Row | None:
    import hashlib
    import hmac

    with connect() as connection:
        row = connection.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if row is None:
        return None
    supplied_hash = hashlib.sha256(guest_token.encode()).hexdigest()
    return row if hmac.compare_digest(row['guest_token_hash'], supplied_hash) else None


def update_project(project_id: str, *, name: str | None = None, style: str | None = None, settings: dict | None = None) -> dict:
    with connect() as connection:
        row = connection.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        next_style = style if style is not None else row['style']
        if style is None:
            template_id = row['template_id']
        else:
            template = connection.execute(
                'SELECT id FROM packaging_templates WHERE style=? AND available=1 ORDER BY version DESC LIMIT 1',
                (next_style,),
            ).fetchone()
            template_id = template['id'] if template else None
        values = {
            'name': (name if name is not None else row['name'])[:200],
            'style': next_style,
            'template_id': template_id,
            'settings_json': json.dumps(settings if settings is not None else json.loads(row['settings_json']), separators=(',', ':')),
            'updated_at': utc_now(),
        }
        connection.execute('UPDATE projects SET name=:name, style=:style, template_id=:template_id, settings_json=:settings_json, updated_at=:updated_at WHERE id=:id', {**values, 'id': project_id})
        return dict(connection.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone())


def add_asset(project_id: str, asset_type: str, storage_key: str, mime_type: str, size_bytes: int, metadata: dict | None = None) -> dict:
    asset_id = str(uuid.uuid4())
    with connect() as connection:
        connection.execute(
            '''INSERT INTO assets(id, project_id, asset_type, storage_key, mime_type, size_bytes, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (asset_id, project_id, asset_type, storage_key, mime_type, size_bytes,
             json.dumps(metadata or {}, separators=(',', ':')), utc_now()),
        )
        return dict(connection.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone())


def get_asset(project_id: str, asset_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute('SELECT * FROM assets WHERE id=? AND project_id=?', (asset_id, project_id)).fetchone()
    return dict(row) if row else None


def delete_asset(project_id: str, asset_id: str) -> str | None:
    with connect() as connection:
        row = connection.execute('SELECT storage_key FROM assets WHERE project_id=? AND id=?', (project_id, asset_id)).fetchone()
        if row is None:
            return None
        connection.execute('DELETE FROM assets WHERE project_id=? AND id=?', (project_id, asset_id))
    return row['storage_key']


def create_task(project_id: str, task_type: str, *, input_asset_id: str | None = None, provider: str | None = None, parameters: dict | None = None) -> dict:
    task_id = str(uuid.uuid4())
    with connect() as connection:
        connection.execute(
                '''INSERT INTO generation_tasks(id, project_id, task_type, status, input_asset_id, provider, parameters_json, attempts, created_at, started_at)
                    VALUES (?, ?, ?, 'running', ?, ?, ?, 1, ?, ?)''',
                (task_id, project_id, task_type, input_asset_id, provider,
                 json.dumps(parameters or {}, separators=(',', ':')), utc_now(), utc_now()),
        )
        connection.execute("UPDATE projects SET status='processing', updated_at=? WHERE id=?", (utc_now(), project_id))
        return dict(connection.execute('SELECT * FROM generation_tasks WHERE id=?', (task_id,)).fetchone())


def finish_task(task_id: str, *, status: str, output_asset_id: str | None = None, error_message: str | None = None) -> None:
    now = utc_now()
    with connect() as connection:
        task = connection.execute('SELECT project_id FROM generation_tasks WHERE id=?', (task_id,)).fetchone()
        if task is None:
            raise KeyError(task_id)
        connection.execute(
            'UPDATE generation_tasks SET status=?, output_asset_id=?, error_message=?, started_at=COALESCE(started_at, ?), finished_at=? WHERE id=?',
            (status, output_asset_id, error_message, now, now, task_id),
        )
        remaining = connection.execute("SELECT 1 FROM generation_tasks WHERE project_id=? AND status IN ('queued','running') LIMIT 1", (task['project_id'],)).fetchone()
        project_status = 'processing' if remaining else ('ready' if status == 'succeeded' else 'error')
        connection.execute('UPDATE projects SET status=?, updated_at=? WHERE id=?', (project_status, now, task['project_id']))


def project_snapshot(project_id: str) -> dict:
    with connect() as connection:
        project = connection.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if project is None:
            raise KeyError(project_id)
        assets = connection.execute('SELECT * FROM assets WHERE project_id=? ORDER BY created_at', (project_id,)).fetchall()
        tasks = connection.execute('SELECT * FROM generation_tasks WHERE project_id=? ORDER BY created_at', (project_id,)).fetchall()
    return {
        'id': project['id'], 'name': project['name'], 'style': project['style'],
        'template_id': project['template_id'],
        'settings': json.loads(project['settings_json']), 'status': project['status'],
        'created_at': project['created_at'], 'updated_at': project['updated_at'],
        'assets': [_asset_dict(row) for row in assets],
        'tasks': [_task_dict(row) for row in tasks],
    }


def _asset_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result.pop('storage_key', None)
    result['metadata'] = json.loads(result.pop('metadata_json'))
    result['url'] = f"/api/projects/{result['project_id']}/assets/{result['id']}/content"
    return result


def asset_response(asset: dict) -> dict:
    result = dict(asset)
    result.pop('storage_key', None)
    result['metadata'] = json.loads(result.pop('metadata_json'))
    result['url'] = f"/api/projects/{result['project_id']}/assets/{result['id']}/content"
    return result


def _task_dict(row: sqlite3.Row) -> dict:
    return {**dict(row), 'parameters': json.loads(row['parameters_json'])}


def delete_project(project_id: str) -> list[str]:
    with connect() as connection:
        rows = connection.execute('SELECT storage_key FROM assets WHERE project_id=?', (project_id,)).fetchall()
        connection.execute('DELETE FROM projects WHERE id=?', (project_id,))
    return [row['storage_key'] for row in rows]