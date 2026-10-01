import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / 'uploads' / 'images'
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    'image/jpg': 'jpg',
    'image/jpeg': 'jpg',
    'image/pjpeg': 'jpg',
    'image/png': 'png',
}


def _detect_image_extension(file_bytes: bytes, content_type: str | None) -> str | None:
    if content_type in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[content_type]

    if file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'

    if file_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpg'

    return None


def save_uploaded_image(upload_file: UploadFile) -> dict:
    if upload_file is None or not getattr(upload_file, 'filename', None):
        raise HTTPException(status_code=400, detail='Файл не найден.')

    file_bytes = upload_file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail='Файл пуст.')

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='Размер изображения не должен превышать 10 МБ.')

    extension = _detect_image_extension(file_bytes, upload_file.content_type)
    if extension is None:
        raise HTTPException(status_code=400, detail='Поддерживаются только изображения JPG, JPEG и PNG.')

    file_name = f'{uuid.uuid4()}.{extension}'
    destination = UPLOAD_ROOT / file_name

    with destination.open('wb') as file_handle:
        file_handle.write(file_bytes)

    return {
        'success': True,
        'filename': file_name,
        'content_type': 'image/png' if extension == 'png' else 'image/jpeg',
        'size': len(file_bytes),
        'url': f'/uploads/images/{file_name}',
    }
