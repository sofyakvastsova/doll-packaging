from enum import Enum

from fastapi import APIRouter, File, Form, UploadFile

from app.services.ai.photopanda import generate_doll_illustration
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
    result = await generate_doll_illustration(source_filename, style.value)
    saved = save_generated_image(result.image_bytes, result.content_type)
    return {
        **saved,
        'model_id': result.model_id,
        'resolution': result.resolution,
        'attempts': result.attempts,
        'started_at': result.started_at,
        'ended_at': result.ended_at,
        'duration_ms': result.duration_ms,
    }
