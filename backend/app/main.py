from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.images import router as images_router
from app.api.projects import router as projects_router
from app.db.database import initialize_database

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / 'uploads' / 'images'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
initialize_database()

app = FastAPI(title='Doll Packaging API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/uploads/images', StaticFiles(directory=str(UPLOAD_DIR)), name='images')
app.include_router(images_router)
app.include_router(projects_router)


@app.get('/')
def read_root():
    return {'message': 'Backend is working'}


@app.get('/api/health')
def health_check():
    return {'status': 'ok'}
