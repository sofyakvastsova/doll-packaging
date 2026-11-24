import json
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import Response

from app.db import database
from app.storage.local import local_storage

router = APIRouter(prefix='/api/projects', tags=['projects'])


class ProjectStyle(str, Enum):
    BRATZ = 'bratz'
    MONSTER_HIGH = 'monster_high'


class ProjectCreate(BaseModel):
    name: str = Field(default='Новый проект', max_length=200)
    style: ProjectStyle
    settings: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    style: ProjectStyle | None = None
    settings: dict | None = None


def _authorized_project(project_id: str, guest_token: str | None):
    if not guest_token:
        raise HTTPException(status_code=401, detail='Нужен токен доступа к гостевому проекту.')
    project = database.authorize_project(project_id, guest_token)
    if project is None:
        raise HTTPException(status_code=404, detail='Проект не найден.')
    return project


@router.post('', status_code=201)
def create_project(payload: ProjectCreate):
    project, guest_token = database.create_project(payload.style.value, payload.name, payload.settings)
    snapshot = database.project_snapshot(project['id'])
    return {**snapshot, 'guest_token': guest_token}


@router.get('/{project_id}')
def get_project(project_id: str, x_guest_token: str | None = Header(default=None)):
    _authorized_project(project_id, x_guest_token)
    return database.project_snapshot(project_id)


@router.patch('/{project_id}')
def patch_project(project_id: str, payload: ProjectUpdate, x_guest_token: str | None = Header(default=None)):
    _authorized_project(project_id, x_guest_token)
    try:
        database.update_project(
            project_id,
            name=payload.name,
            style=payload.style.value if payload.style else None,
            settings=payload.settings,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail='Недопустимый стиль проекта.') from error
    return database.project_snapshot(project_id)


@router.delete('/{project_id}', status_code=204)
def remove_project(project_id: str, x_guest_token: str | None = Header(default=None)):
    _authorized_project(project_id, x_guest_token)
    with local_storage.exclusive_lock():
        for storage_key in database.delete_project(project_id):
            local_storage.delete(storage_key)
    return Response(status_code=204)


@router.post('/{project_id}/assets', status_code=201)
async def upload_project_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    asset_metadata: str = Form(default='{}'),
    x_guest_token: str | None = Header(default=None),
):
    _authorized_project(project_id, x_guest_token)
    content = await file.read(25 * 1024 * 1024 + 1)
    mime_type = (file.content_type or '').split(';', 1)[0].strip().lower()
    allowed = {
        'original_photo': {'image/jpeg', 'image/png'},
        'generated_doll': {'image/jpeg', 'image/png', 'image/webp'},
        'transparent_doll': {'image/png'},
        'logo': {'image/jpeg', 'image/png'},
        'packaging_preview': {'image/png'},
        'pdf': {'application/pdf'},
        'intermediate': {'image/png', 'image/jpeg', 'image/webp'},
    }
    if asset_type not in allowed or mime_type not in allowed[asset_type]:
        raise HTTPException(status_code=400, detail='Формат файла не разрешён для этого типа asset.')
    magic = {
        'image/png': content.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/jpeg': content.startswith(b'\xff\xd8\xff'),
        'image/webp': content.startswith(b'RIFF') and content[8:12] == b'WEBP',
        'application/pdf': content.startswith(b'%PDF-'),
    }
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413 if content else 400, detail='Файл пуст или превышает допустимый размер.')
    if not magic[mime_type]:
        raise HTTPException(status_code=400, detail='Содержимое файла не соответствует указанному формату.')
    try:
        metadata = json.loads(asset_metadata)
    except ValueError as error:
        raise HTTPException(status_code=400, detail='Метаданные файла имеют неверный формат.') from error
    if not isinstance(metadata, dict) or len(asset_metadata) > 4000:
        raise HTTPException(status_code=400, detail='Метаданные файла имеют неверный формат.')
    if set(metadata) - {'slot'} or (metadata.get('slot') is not None and metadata['slot'] not in {'outer_background', 'inner_background'}):
        raise HTTPException(status_code=400, detail='Недопустимые метаданные файла.')
    with local_storage.exclusive_lock():
        storage_key = local_storage.save(project_id, asset_type, content, mime_type)
        try:
            asset = database.add_asset(project_id, asset_type, storage_key, mime_type, len(content), {
                'original_name': Path(file.filename or '').name[:255],
                **metadata,
            })
        except Exception:
            local_storage.delete(storage_key)
            raise
    return database.asset_response(asset)


@router.get('/{project_id}/assets/{asset_id}/content')
def get_project_asset(project_id: str, asset_id: str, x_guest_token: str | None = Header(default=None)):
    _authorized_project(project_id, x_guest_token)
    asset = database.get_asset(project_id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail='Файл проекта не найден.')
    try:
        content = local_storage.read(asset['storage_key'])
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail='Файл проекта не найден в хранилище.') from error
    return Response(content, media_type=asset['mime_type'], headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.delete('/{project_id}/assets/{asset_id}', status_code=204)
def remove_project_asset(project_id: str, asset_id: str, x_guest_token: str | None = Header(default=None)):
    _authorized_project(project_id, x_guest_token)
    with local_storage.exclusive_lock():
        storage_key = database.delete_asset(project_id, asset_id)
        if storage_key is None:
            raise HTTPException(status_code=404, detail='Файл проекта не найден.')
        local_storage.delete(storage_key)
    return Response(status_code=204)