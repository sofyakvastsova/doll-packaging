import fcntl
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / '.env', override=False)
_configured_storage = Path(os.getenv('FILE_STORAGE_ROOT', 'storage')).expanduser()
DEFAULT_STORAGE_ROOT = (
    (BACKEND_ROOT / _configured_storage).resolve()
    if not _configured_storage.is_absolute()
    else _configured_storage.resolve()
)
MAX_PROJECT_FILE_BYTES = 25 * 1024 * 1024
PROJECT_ID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
ASSET_DIRECTORIES = {
    'original_photo': 'originals',
    'generated_doll': 'generated',
    'transparent_doll': 'processed',
    'logo': 'logos',
    'packaging_preview': 'previews',
    'pdf': 'exports',
    'intermediate': 'intermediate',
}
ALLOWED_EXTENSIONS = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
    'application/pdf': '.pdf',
}


class LocalFileStorage:
    def __init__(self, root: Path | str = DEFAULT_STORAGE_ROOT):
        self.root = Path(root).expanduser().resolve()

    @contextmanager
    def exclusive_lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        lock_path = self.root / '.backup.lock'
        with lock_path.open('a+b') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def save(self, project_id: str, asset_type: str, content: bytes, mime_type: str) -> str:
        project = self._project_id(project_id)
        directory = ASSET_DIRECTORIES.get(asset_type)
        extension = ALLOWED_EXTENSIONS.get(mime_type.split(';', 1)[0].strip().lower())
        if directory is None or extension is None:
            raise HTTPException(status_code=400, detail='Неподдерживаемый тип файла проекта.')
        limit = 10 * 1024 * 1024 if asset_type in {'original_photo', 'logo'} else MAX_PROJECT_FILE_BYTES
        if not content or len(content) > limit:
            raise HTTPException(status_code=413 if content else 400, detail='Файл пуст или превышает допустимый размер.')

        file_name = f'{uuid.uuid4()}{extension}'
        relative_key = Path('projects') / project / directory / file_name
        destination = self._resolve(relative_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as file_handle:
            file_handle.write(content)
        return relative_key.as_posix()

    def read(self, storage_key: str) -> bytes:
        return self._resolve_key(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._resolve_key(storage_key)
        path.unlink(missing_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = Path(storage_key)
        if candidate.is_absolute() or '..' in candidate.parts or not candidate.parts or candidate.parts[0] != 'projects':
            raise HTTPException(status_code=400, detail='Некорректный ключ файла.')
        return self._resolve(candidate)

    def _resolve(self, relative_path: Path) -> Path:
        resolved = (self.root / relative_path).resolve()
        if not resolved.is_relative_to(self.root):
            raise HTTPException(status_code=400, detail='Путь файла выходит за пределы хранилища.')
        return resolved

    @staticmethod
    def _project_id(project_id: str) -> str:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise HTTPException(status_code=400, detail='Некорректный идентификатор проекта.')
        return project_id


local_storage = LocalFileStorage()