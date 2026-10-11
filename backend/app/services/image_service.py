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
    if file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = 'png'
    elif file_bytes.startswith(b'\xff\xd8\xff'):
        extension = 'jpg'
    else:
        return None

    expected_extension = ALLOWED_CONTENT_TYPES.get(content_type or '')
    if expected_extension is not None and expected_extension != extension:
        return None
    if content_type and content_type not in ALLOWED_CONTENT_TYPES and content_type != 'application/octet-stream':
        return None
    return extension


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


def load_uploaded_image(filename: str) -> tuple[bytes, str]:
    candidate = Path(filename)
    if candidate.name != filename or candidate.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
        raise HTTPException(status_code=400, detail='Исходное изображение указано некорректно.')

    try:
        image_id = uuid.UUID(candidate.stem)
    except ValueError as error:
        raise HTTPException(status_code=400, detail='Исходное изображение указано некорректно.') from error

    extension = 'jpg' if candidate.suffix.lower() == '.jpeg' else candidate.suffix.lower().lstrip('.')
    image_path = UPLOAD_ROOT / f'{image_id}.{extension}'
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail='Загруженное исходное изображение не найдено.')

    image_bytes = image_path.read_bytes()
    content_type = 'image/png' if extension == 'png' else 'image/jpeg'
    if _detect_image_extension(image_bytes, content_type) != extension:
        raise HTTPException(status_code=400, detail='Исходное изображение повреждено или имеет неверный формат.')
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='Размер изображения не должен превышать 10 МБ.')

    return image_bytes, image_path.name


def save_generated_image(image_bytes: bytes, content_type: str) -> dict:
    content_type = content_type.split(';', 1)[0].strip().lower()
    formats = {
        'image/png': ('png', lambda data: data.startswith(b'\x89PNG\r\n\x1a\n')),
        'image/jpeg': ('jpg', lambda data: data.startswith(b'\xff\xd8\xff')),
        'image/webp': ('webp', lambda data: data.startswith(b'RIFF') and data[8:12] == b'WEBP'),
    }
    image_format = formats.get(content_type)
    if image_format is None or not image_bytes or not image_format[1](image_bytes):
        raise HTTPException(status_code=502, detail='Результат PhotoPanda не является корректным изображением.')
    if len(image_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=502, detail='Размер результата PhotoPanda превышает допустимый.')

    extension = image_format[0]
    file_name = f'{uuid.uuid4()}.{extension}'
    (UPLOAD_ROOT / file_name).write_bytes(image_bytes)
    return {
        'success': True,
        'filename': file_name,
        'content_type': content_type,
        'size': len(image_bytes),
        'url': f'/uploads/images/{file_name}',
    }
