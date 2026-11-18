from enum import Enum

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.services.ai.photopanda import generate_doll_illustration
from app.services.background_removal import BackgroundRemovalError, initialize_background_removal, prepare_doll_image
from app.services.image_service import save_generated_image, save_uploaded_image

router = APIRouter(prefix='/api', tags=['images'])


class DollStyle(str, Enum):
    BRATZ = 'bratz'
    MONSTER_HIGH = 'monster_high'


@router.post('/images/upload')
async def upload_image(file: UploadFile = File(...)):
    return save_uploaded_image(file)


@router.post('/images/generate')
async def generate_image(
    source_filename: str = Form(...),
    style: DollStyle = Form(...),
):
    if style == DollStyle.MONSTER_HIGH:
        try:
            await run_in_threadpool(initialize_background_removal)
        except BackgroundRemovalError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    result = await generate_doll_illustration(source_filename, style.value)
    saved = save_generated_image(result.image_bytes, result.content_type)
    if style == DollStyle.MONSTER_HIGH:
        try:
            prepared = await run_in_threadpool(prepare_doll_image, result.image_bytes)
        except BackgroundRemovalError as error:
            raise HTTPException(status_code=502, detail=f'{error} Исходный результат сохранён: {saved["url"]}') from error
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
