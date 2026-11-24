from enum import Enum
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.db import database
from app.api.projects import _authorized_project
from app.services.ai.photopanda import generate_doll_illustration
from app.services.background_removal import BackgroundRemovalError, initialize_background_removal, prepare_doll_image
from app.services.image_service import save_generated_image, save_uploaded_image
from app.storage.local import local_storage

router = APIRouter(prefix='/api', tags=['images'])


class DollStyle(str, Enum):
    BRATZ = 'bratz'
    MONSTER_HIGH = 'monster_high'


def _save_project_asset(project_id: str, asset_type: str, content: bytes, mime_type: str, metadata: dict):
    with local_storage.exclusive_lock():
        storage_key = local_storage.save(project_id, asset_type, content, mime_type)
        try:
            return database.add_asset(project_id, asset_type, storage_key, mime_type, len(content), metadata)
        except Exception:
            local_storage.delete(storage_key)
            raise


@router.post('/images/upload')
async def upload_image(file: UploadFile = File(...)):
    with local_storage.exclusive_lock():
        return save_uploaded_image(file)


@router.post('/images/generate')
async def generate_image(
    source_filename: str = Form(...),
    style: DollStyle = Form(...),
    project_id: str | None = Form(default=None),
    guest_token: str | None = Form(default=None),
    x_guest_token: str | None = Header(default=None),
):
    if project_id:
        return await _generate_project_image(source_filename, style, project_id, guest_token or x_guest_token)

    if style == DollStyle.MONSTER_HIGH:
        try:
            await run_in_threadpool(initialize_background_removal)
        except BackgroundRemovalError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    result = await generate_doll_illustration(source_filename, style.value)
    with local_storage.exclusive_lock():
        saved = save_generated_image(result.image_bytes, result.content_type)
    if style == DollStyle.MONSTER_HIGH:
        try:
            prepared = await run_in_threadpool(prepare_doll_image, result.image_bytes)
        except BackgroundRemovalError as error:
            raise HTTPException(status_code=502, detail=f'{error} Исходный результат сохранён: {saved["url"]}') from error
        with local_storage.exclusive_lock():
            saved = save_generated_image(prepared.png_bytes, 'image/png')
        saved.update({'width': prepared.width, 'height': prepared.height})
    return {
        **saved,
        'model_id': result.model_id,
        'resolution': result.resolution,
        'attempts': result.attempts,
        'started_at': result.started_at,
        'ended_at': result.ended_at,
        'duration_ms': result.duration_ms,
    }


async def _generate_project_image(source_asset_id: str, style: DollStyle, project_id: str, guest_token: str | None):
    project = _authorized_project(project_id, guest_token)
    if project['style'] != style.value:
        raise HTTPException(status_code=409, detail='Стиль запроса не совпадает со стилем проекта.')
    source_asset = database.get_asset(project_id, source_asset_id)
    if source_asset is None or source_asset['asset_type'] != 'original_photo':
        raise HTTPException(status_code=404, detail='Исходное фото проекта не найдено.')

    source_bytes = local_storage.read(source_asset['storage_key'])
    source_name = Path(source_asset['storage_key']).name
    if style == DollStyle.MONSTER_HIGH:
        try:
            await run_in_threadpool(initialize_background_removal)
        except BackgroundRemovalError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    generation_task = database.create_task(
        project_id,
        'doll_generation',
        input_asset_id=source_asset_id,
        provider='photopanda',
        parameters={'style': style.value},
    )
    try:
        result = await generate_doll_illustration(source_name, style.value, source_image=(source_bytes, source_name))
        generated_asset = _save_project_asset(project_id, 'generated_doll', result.image_bytes, result.content_type, {
            'model_id': result.model_id,
            'resolution': result.resolution,
        })
    except Exception as error:
        safe_message = error.detail if isinstance(error, HTTPException) else type(error).__name__
        database.finish_task(generation_task['id'], status='failed', error_message=safe_message[:1000])
        raise
    database.finish_task(generation_task['id'], status='succeeded', output_asset_id=generated_asset['id'])

    output_asset = generated_asset
    background_task = None
    if style == DollStyle.MONSTER_HIGH:
        background_task = database.create_task(
            project_id,
            'background_removal',
            input_asset_id=generated_asset['id'],
            provider='rembg:isnet-general-use',
        )
        try:
            prepared = await run_in_threadpool(prepare_doll_image, result.image_bytes)
            output_asset = _save_project_asset(project_id, 'transparent_doll', prepared.png_bytes, 'image/png', {
                'width': prepared.width,
                'height': prepared.height,
            })
            database.finish_task(background_task['id'], status='succeeded', output_asset_id=output_asset['id'])
        except Exception as error:
            safe_message = error.detail if isinstance(error, HTTPException) else type(error).__name__
            database.finish_task(background_task['id'], status='failed', error_message=safe_message[:1000])
            raise HTTPException(status_code=502, detail=f'Удаление фона не выполнено. Исходная генерация сохранена в проекте как asset {generated_asset["id"]}.') from error

    response = {
        **database.asset_response(output_asset),
        'success': True,
        'task_id': generation_task['id'],
        'background_task_id': background_task['id'] if background_task else None,
        'generated_asset': database.asset_response(generated_asset),
        'model_id': result.model_id,
        'resolution': result.resolution,
        'attempts': result.attempts,
        'started_at': result.started_at,
        'ended_at': result.ended_at,
        'duration_ms': result.duration_ms,
    }
    if style == DollStyle.MONSTER_HIGH:
        response.update({'width': prepared.width, 'height': prepared.height})
    return response
