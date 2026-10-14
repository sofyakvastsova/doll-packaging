import json
import logging
import mimetypes
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.services.image_service import load_uploaded_image
from app.services.ai.config import (
    MAX_INPUT_SIZE_BYTES,
    MAX_OUTPUT_SIZE_BYTES,
    PROMPT_EDIT_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    STYLE_PROMPT,
    STYLE_REFERENCE_PATHS,
    PhotoPandaSettings,
)

logger = logging.getLogger('app.ai.photopanda')
ALLOWED_MODELS = {'nano-banana-lite', 'nano-banana-2', 'gpt-image-2-medium', 'gpt-image-2-high'}
ALLOWED_RESOLUTIONS = {'1K', '2K', '4K'}


@dataclass(frozen=True)
class PhotoPandaResult:
    image_bytes: bytes
    content_type: str
    model_id: str
    resolution: str
    attempts: int
    started_at: str
    ended_at: str
    duration_ms: int


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _image_content_type(image_bytes: bytes) -> str | None:
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if image_bytes.startswith(b'RIFF') and image_bytes[8:12] == b'WEBP':
        return 'image/webp'
    return None


def _reference_files_for_style(style: str) -> list[tuple[bytes, str, str]]:
    raw_reference = STYLE_REFERENCE_PATHS.get(style)
    if raw_reference is None:
        raise _error(422, 'Выбран неподдерживаемый стиль куклы.')

    if isinstance(raw_reference, (str, Path)):
        reference_paths = [Path(raw_reference)]
    elif isinstance(raw_reference, (list, tuple, set)):
        reference_paths = [Path(path) for path in raw_reference]
    else:
        raise _error(503, 'Конфигурация стиля содержит некорректные эталоны изображений.')

    if not reference_paths:
        raise _error(503, f'Для стиля {style} пока не добавлены эталоны изображения.')
    if len(reference_paths) > 4:
        raise _error(503, 'PhotoPanda принимает не более 4 эталонных изображений.')

    reference_files: list[tuple[bytes, str, str]] = []
    for reference_path in reference_paths:
        if not reference_path.is_file():
            raise _error(503, f'Для стиля {style} пока не добавлен эталон изображения: {reference_path.name}')

        try:
            reference_bytes = reference_path.read_bytes()
        except OSError as error:
            raise _error(503, 'Не удалось прочитать эталон изображения стиля.') from error

        if not reference_bytes or len(reference_bytes) > MAX_INPUT_SIZE_BYTES:
            raise _error(503, 'Файл эталонного изображения пуст или превышает 10 МБ.')

        content_type = _image_content_type(reference_bytes)
        if content_type is None:
            raise _error(503, 'Файл эталонного изображения имеет неподдерживаемый формат.')
        reference_files.append((reference_bytes, reference_path.name, content_type))

    return reference_files


def _validate_output_url(output_url: object) -> str:
    if not isinstance(output_url, str):
        raise _error(502, 'PhotoPanda не вернул ссылку на результат.')
    parsed = urlparse(output_url)
    if parsed.scheme != 'https' or parsed.hostname not in {'photopanda.ru', 'www.photopanda.ru'}:
        raise _error(502, 'PhotoPanda вернул некорректную ссылку на результат.')
    return output_url


def _record_metrics(
    *,
    started_at: str,
    started_clock: float,
    outcome: str,
    error_type: str | None,
    model_id: str,
    resolution: str,
    attempts: int,
) -> tuple[str, int]:
    ended_at = datetime.now(timezone.utc).isoformat()
    duration_ms = round((time.monotonic() - started_clock) * 1000)
    logger.info(json.dumps({
        'event': 'photopanda_prompt_edit',
        'started_at': started_at,
        'ended_at': ended_at,
        'duration_ms': duration_ms,
        'outcome': outcome,
        'error_type': error_type,
        'model_id': model_id,
        'resolution': resolution,
        'attempts': attempts,
    }, separators=(',', ':')))
    return ended_at, duration_ms


async def generate_doll_illustration(
    source_filename: str,
    style: str,
    *,
    settings: PhotoPandaSettings | None = None,
    client: httpx.AsyncClient | None = None,
) -> PhotoPandaResult:
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()
    settings = settings or PhotoPandaSettings.from_environment()
    attempts = 0
    outcome = 'error'
    error_type: str | None = None

    try:
        if not settings.api_key:
            raise _error(503, 'PhotoPanda не настроен: задайте PHOTOPANDA_API_KEY в backend/.env.')
        if settings.model_id not in ALLOWED_MODELS or settings.resolution not in ALLOWED_RESOLUTIONS:
            raise _error(503, 'Настройки модели PhotoPanda некорректны.')

        source_bytes, safe_source_name = load_uploaded_image(source_filename)
        source_type = _image_content_type(source_bytes)
        if source_type is None:
            raise _error(400, 'Исходный файл повреждён или имеет неподдерживаемый формат.')
        reference_files = _reference_files_for_style(style)

        own_client = client is None
        if client is None:
            timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=20.0)
            client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

        attempts = 1
        files = [('file', (safe_source_name, source_bytes, source_type))]
        files.extend(
            ('reference', (reference_name, reference_bytes, reference_type))
            for reference_bytes, reference_name, reference_type in reference_files
        )
        form_data = {
            'operation': 'prompt_edit',
            'prompt': STYLE_PROMPT,
            'modelId': settings.model_id,
            'resolution': settings.resolution,
        }

        try:
            response = await client.post(
                PROMPT_EDIT_ENDPOINT,
                headers={'X-API-Key': settings.api_key},
                data=form_data,
                files=files,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as error:
            error_type = 'TimeoutError'
            raise _error(504, 'PhotoPanda не ответил вовремя. Исходное фото сохранено; можно повторить позже.') from error
        except httpx.RequestError as error:
            error_type = 'ConnectionError'
            raise _error(503, 'Не удалось подключиться к PhotoPanda. Исходное фото сохранено.') from error

        if response.status_code >= 400:
            error_type = f'PhotoPandaHTTP{response.status_code}'
            mapped = {
                400: (400, 'PhotoPanda отклонил запрос или файл. Проверьте формат изображения и настройки.'),
                401: (502, 'PhotoPanda отклонил API-ключ. Проверьте PHOTOPANDA_API_KEY.'),
                402: (402, 'Недостаточно средств на балансе PhotoPanda.'),
                413: (413, 'Файл превышает лимит PhotoPanda.'),
                429: (429, 'PhotoPanda ограничил частоту запросов. Попробуйте позже.'),
                503: (503, 'Операция PhotoPanda временно недоступна.'),
            }
            status_code, detail = mapped.get(response.status_code, (502, 'PhotoPanda временно не смог обработать изображение.'))
            raise _error(status_code, detail)

        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as error:
            error_type = 'InvalidProviderResponse'
            raise _error(502, 'PhotoPanda вернул некорректный ответ.') from error

        if not isinstance(payload, dict):
            error_type = 'InvalidProviderResponse'
            raise _error(502, 'PhotoPanda вернул некорректный ответ.')
        if payload.get('status') not in (None, 'done', 'completed'):
            error_type = 'ProviderJobFailed'
            raise _error(502, 'PhotoPanda не завершил обработку изображения.')
        output_url = _validate_output_url(payload.get('outputUrl'))

        try:
            async with client.stream('GET', output_url, timeout=60.0) as output_response:
                if output_response.status_code != 200:
                    error_type = 'ResultDownloadError'
                    raise _error(502, 'Не удалось скачать готовое изображение из PhotoPanda.')
                content_type = output_response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
                chunks: list[bytes] = []
                total_size = 0
                async for chunk in output_response.aiter_bytes():
                    total_size += len(chunk)
                    if total_size > MAX_OUTPUT_SIZE_BYTES:
                        error_type = 'ResultTooLarge'
                        raise _error(502, 'Результат PhotoPanda превышает допустимый размер.')
                    chunks.append(chunk)
        except httpx.TimeoutException as error:
            error_type = 'ResultDownloadTimeout'
            raise _error(504, 'Истекло время ожидания скачивания результата PhotoPanda.') from error
        except httpx.RequestError as error:
            error_type = 'ResultDownloadError'
            raise _error(502, 'Не удалось скачать готовое изображение из PhotoPanda.') from error

        image_bytes = b''.join(chunks)
        detected_type = _image_content_type(image_bytes)
        if not image_bytes or detected_type is None or detected_type != content_type:
            error_type = 'InvalidImageResult'
            raise _error(502, 'PhotoPanda вернул файл, который не является корректным изображением.')

        outcome = 'success'
        error_type = None
        ended_at, duration_ms = _record_metrics(
            started_at=started_at,
            started_clock=started_clock,
            outcome=outcome,
            error_type=error_type,
            model_id=settings.model_id,
            resolution=settings.resolution,
            attempts=attempts,
        )
        return PhotoPandaResult(
            image_bytes=image_bytes,
            content_type=detected_type,
            model_id=settings.model_id,
            resolution=settings.resolution,
            attempts=attempts,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
        )
    except HTTPException as error:
        if error_type is None:
            error_type = f'ApplicationHTTP{error.status_code}'
        raise
    except Exception as error:
        error_type = type(error).__name__
        raise _error(502, 'Внутренняя ошибка модуля генерации PhotoPanda.') from error
    finally:
        if outcome != 'success':
            _record_metrics(
                started_at=started_at,
                started_clock=started_clock,
                outcome=outcome,
                error_type=error_type,
                model_id=settings.model_id,
                resolution=settings.resolution,
                attempts=attempts,
            )
        if client is not None and 'own_client' in locals() and own_client:
            await client.aclose()
