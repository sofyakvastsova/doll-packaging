from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api import images
from app.db import database
from app.main import app
from app.storage.local import LocalFileStorage


def make_png():
    image = Image.new('RGB', (40, 60), 'white')
    ImageDraw.Draw(image).rectangle((10, 5, 29, 49), fill='black')
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


@pytest.fixture
def project_client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'projects.sqlite3')
    database.initialize_database()
    monkeypatch.setattr('app.api.projects.local_storage', LocalFileStorage(tmp_path / 'storage'))
    monkeypatch.setattr('app.api.images.local_storage', LocalFileStorage(tmp_path / 'storage'))
    return TestClient(app)


def test_guest_project_requires_token_and_uploads_private_asset(project_client):
    created = project_client.post('/api/projects', json={'style': 'bratz', 'name': 'Test'}).json()
    project_id = created['id']
    token = created['guest_token']
    assert project_client.get(f'/api/projects/{project_id}').status_code == 401
    assert project_client.get(f'/api/projects/{project_id}', headers={'X-Guest-Token': 'wrong'}).status_code == 404

    uploaded = project_client.post(
        f'/api/projects/{project_id}/assets',
        headers={'X-Guest-Token': token},
        data={'asset_type': 'original_photo'},
        files={'file': ('my photo.png', make_png(), 'image/png')},
    )
    assert uploaded.status_code == 201
    asset = uploaded.json()
    assert 'storage_key' not in asset
    assert asset['metadata']['original_name'] == 'my photo.png'
    content = project_client.get(asset['url'], headers={'X-Guest-Token': token})
    assert content.status_code == 200 and content.content.startswith(b'\x89PNG')
    assert project_client.get(asset['url']).status_code == 401


def test_project_generation_creates_task_and_saves_generated_asset(project_client, monkeypatch):
    created = project_client.post('/api/projects', json={'style': 'bratz'}).json()
    project_id = created['id']
    token = created['guest_token']
    uploaded = project_client.post(
        f'/api/projects/{project_id}/assets',
        headers={'X-Guest-Token': token},
        data={'asset_type': 'original_photo'},
        files={'file': ('source.png', make_png(), 'image/png')},
    ).json()
    source = make_png()

    async def fake_generate(filename, style, *, source_image=None):
        assert filename.endswith('.png')
        assert style == 'bratz'
        assert source_image and source_image[0].startswith(b'\x89PNG')
        return SimpleNamespace(image_bytes=source, content_type='image/png', model_id='model', resolution='1K',
                               attempts=1, started_at='start', ended_at='end', duration_ms=1)

    monkeypatch.setattr(images, 'generate_doll_illustration', fake_generate)
    response = project_client.post('/api/images/generate', data={
        'source_filename': uploaded['id'], 'style': 'bratz', 'project_id': project_id, 'guest_token': token,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload['asset_type'] == 'generated_doll'
    assert project_client.get(payload['url'], headers={'X-Guest-Token': token}).content == source
    snapshot = project_client.get(f'/api/projects/{project_id}', headers={'X-Guest-Token': token}).json()
    assert snapshot['status'] == 'ready'
    assert len(snapshot['tasks']) == 1 and snapshot['tasks'][0]['status'] == 'succeeded'
    assert len(snapshot['assets']) == 2


def test_project_generation_rejects_missing_asset(project_client):
    project = project_client.post('/api/projects', json={'style': 'bratz'}).json()
    response = project_client.post('/api/images/generate', data={
        'source_filename': 'non-existent-asset', 'style': 'bratz',
        'project_id': project['id'], 'guest_token': project['guest_token'],
    })
    assert response.status_code == 404


def test_delete_project_asset_removes_database_row_and_file(project_client):
    project = project_client.post('/api/projects', json={'style': 'bratz'}).json()
    token = project['guest_token']
    uploaded = project_client.post(
        f"/api/projects/{project['id']}/assets",
        headers={'X-Guest-Token': token},
        data={'asset_type': 'original_photo'},
        files={'file': ('source.png', make_png(), 'image/png')},
    ).json()
    response = project_client.delete(
        f"/api/projects/{project['id']}/assets/{uploaded['id']}",
        headers={'X-Guest-Token': token},
    )
    assert response.status_code == 204
    snapshot = project_client.get(f"/api/projects/{project['id']}", headers={'X-Guest-Token': token}).json()
    assert snapshot['assets'] == []
    assert project_client.get(uploaded['url'], headers={'X-Guest-Token': token}).status_code == 404


def test_custom_background_is_a_project_asset_not_inline_data(project_client):
    project = project_client.post('/api/projects', json={'style': 'bratz'}).json()
    response = project_client.post(
        f"/api/projects/{project['id']}/assets",
        headers={'X-Guest-Token': project['guest_token']},
        data={'asset_type': 'intermediate', 'asset_metadata': '{"slot":"outer_background"}'},
        files={'file': ('wallpaper.png', make_png(), 'image/png')},
    )
    assert response.status_code == 201
    asset = response.json()
    assert asset['asset_type'] == 'intermediate'
    assert asset['metadata']['slot'] == 'outer_background'
    assert 'storage_key' not in asset


def test_monster_high_project_tracks_generation_and_background_tasks(project_client, monkeypatch):
    created = project_client.post('/api/projects', json={'style': 'monster_high'}).json()
    project_id = created['id']
    token = created['guest_token']
    uploaded = project_client.post(
        f'/api/projects/{project_id}/assets',
        headers={'X-Guest-Token': token},
        data={'asset_type': 'original_photo'},
        files={'file': ('source.png', make_png(), 'image/png')},
    ).json()
    generated_bytes = make_png()

    async def fake_generate(_filename, _style, *, source_image=None):
        return SimpleNamespace(image_bytes=generated_bytes, content_type='image/png', model_id='model', resolution='1K',
                               attempts=1, started_at='start', ended_at='end', duration_ms=1)

    def fake_prepare(_image_bytes):
        return SimpleNamespace(png_bytes=generated_bytes, width=40, height=60)

    monkeypatch.setattr(images, 'generate_doll_illustration', fake_generate)
    monkeypatch.setattr(images, 'initialize_background_removal', lambda: None)
    monkeypatch.setattr(images, 'prepare_doll_image', fake_prepare)
    response = project_client.post('/api/images/generate', data={
        'source_filename': uploaded['id'], 'style': 'monster_high', 'project_id': project_id, 'guest_token': token,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload['asset_type'] == 'transparent_doll'
    assert payload['width'] == 40 and payload['height'] == 60
    snapshot = project_client.get(f'/api/projects/{project_id}', headers={'X-Guest-Token': token}).json()
    tasks = {task['task_type']: task for task in snapshot['tasks']}
    assert tasks['doll_generation']['status'] == 'succeeded'
    assert tasks['background_removal']['status'] == 'succeeded'
    assert tasks['background_removal']['input_asset_id'] == tasks['doll_generation']['output_asset_id']
    assert tasks['background_removal']['output_asset_id'] == payload['id']
    assert len(snapshot['assets']) == 3