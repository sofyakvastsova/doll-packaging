import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api import images
from app.main import app
from app.services import background_removal, image_service


def make_image():
    image = Image.new('RGB', (100, 140), 'white')
    ImageDraw.Draw(image).rectangle((30, 20, 69, 119), fill='black')
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def setup_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(image_service, 'UPLOAD_ROOT', tmp_path)
    source = make_image()

    async def generate(_filename, _style):
        return SimpleNamespace(image_bytes=source, content_type='image/png', model_id='model', resolution='1K',
                               attempts=1, started_at='start', ended_at='end', duration_ms=1)

    monkeypatch.setattr(images, 'generate_doll_illustration', generate)
    return source


def test_monster_high_returns_prepared_png(monkeypatch, tmp_path):
    setup_provider(monkeypatch, tmp_path)
    monkeypatch.setattr(images, 'initialize_background_removal', lambda: None)

    def remove_background(image):
        alpha = Image.new('L', image.size)
        ImageDraw.Draw(alpha).rectangle((30, 20, 69, 119), fill=255)
        image.putalpha(alpha)
        return image

    monkeypatch.setattr(background_removal, '_remove_background', remove_background)
    response = TestClient(app).post('/api/images/generate', data={'source_filename': 'source.png', 'style': 'monster_high'})
    assert response.status_code == 200
    payload = response.json()
    assert (payload['content_type'], payload['width'], payload['height']) == ('image/png', 48, 108)
    output = Image.open(tmp_path / payload['filename'])
    assert output.mode == 'RGBA'
    assert output.getpixel((0, 0))[3] == 0
    assert len(list(tmp_path.iterdir())) == 2


def test_bratz_preserves_original_response(monkeypatch, tmp_path):
    source = setup_provider(monkeypatch, tmp_path)
    response = TestClient(app).post('/api/images/generate', data={'source_filename': 'source.png', 'style': 'bratz'})
    assert response.status_code == 200
    assert (tmp_path / response.json()['filename']).read_bytes() == source


def test_model_failure_happens_before_generation(monkeypatch, tmp_path):
    setup_provider(monkeypatch, tmp_path)

    def fail():
        raise background_removal.BackgroundRemovalError('Модель недоступна')

    monkeypatch.setattr(images, 'initialize_background_removal', fail)
    response = TestClient(app).post('/api/images/generate', data={'source_filename': 'source.png', 'style': 'monster_high'})
    assert response.status_code == 503
    assert not list(tmp_path.iterdir())


def test_segmentation_failure_keeps_provider_result(monkeypatch, tmp_path):
    source = setup_provider(monkeypatch, tmp_path)
    monkeypatch.setattr(images, 'initialize_background_removal', lambda: None)

    def fail(_image):
        raise background_removal.BackgroundRemovalError('Ошибка обработки')

    monkeypatch.setattr(images, 'prepare_doll_image', fail)
    response = TestClient(app).post('/api/images/generate', data={'source_filename': 'source.png', 'style': 'monster_high'})
    assert response.status_code == 502
    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == source
    assert saved_files[0].name in response.json()['detail']


@pytest.mark.skipif(os.getenv('RUN_REMBG_INTEGRATION') != '1', reason='requires local model and test image')
def test_monster_high_pipeline_with_real_segmentation(monkeypatch, tmp_path):
    test_image = Path(__file__).resolve().parents[2] / 'assets' / 'test.webp'
    if not test_image.is_file():
        pytest.skip('assets/test.webp is not available')
    original = test_image.read_bytes()
    monkeypatch.setattr(image_service, 'UPLOAD_ROOT', tmp_path)

    async def generate(_filename, _style):
        return SimpleNamespace(image_bytes=original, content_type='image/webp', model_id='model', resolution='1K',
                               attempts=1, started_at='start', ended_at='end', duration_ms=1)

    monkeypatch.setattr(images, 'generate_doll_illustration', generate)
    response = TestClient(app).post('/api/images/generate', data={'source_filename': 'source.png', 'style': 'monster_high'})
    assert response.status_code == 200
    payload = response.json()
    output = Image.open(tmp_path / payload['filename'])
    assert output.format == 'PNG' and output.mode == 'RGBA'
    assert output.size == (payload['width'], payload['height'])
    assert output.width < 960 and output.height < 1280
    assert output.getchannel('A').getextrema() == (0, 255)
    assert test_image.read_bytes() == original