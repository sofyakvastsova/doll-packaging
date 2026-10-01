from fastapi import APIRouter, File, UploadFile

from app.services.image_service import save_uploaded_image

router = APIRouter(prefix='/api', tags=['images'])


@router.post('/images/upload')
async def upload_image(file: UploadFile = File(...)):
    return save_uploaded_image(file)
