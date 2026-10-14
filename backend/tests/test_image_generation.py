import asyncio
import json
import uuid

import httpx
import pytest
from fastapi import HTTPException

from app.services import image_service
from app.services.ai import photopanda
from app.services.ai.config import PROMPT_EDIT_ENDPOINT, PhotoPandaSettings, STYLE_PROMPT

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
SOURCE_BYTES = PNG_SIGNATURE + b'user-photo'
OUTPUT_BYTES = PNG_SIGNATURE + b'generated-illustration'


@pytest.fixture
def image_storage(tmp_path, monkeypatch):
	upload_root = tmp_path / 'uploads'
	upload_root.mkdir()
	monkeypatch.setattr(image_service, 'UPLOAD_ROOT', upload_root)
	source_filename = f'{uuid.uuid4()}.png'
	(upload_root / source_filename).write_bytes(SOURCE_BYTES)
	return upload_root, source_filename


def _settings():
	return PhotoPandaSettings(api_key='test-key', model_id='gpt-image-2-medium', resolution='1K')


@pytest.mark.parametrize(
	('style', 'reference_name', 'reference_bytes'),
	[
		('bratz', 'doll-style-reference.png', PNG_SIGNATURE + b'bratz-art-style'),
		('monster_high', 'monster-high-style-reference.png', PNG_SIGNATURE + b'monster-art-style'),
	],
)
def test_photo_edit_sends_user_photo_reference_and_same_prompt(style, reference_name, reference_bytes, image_storage, monkeypatch):
	_, source_filename = image_storage
	reference_path = image_storage[0].parent / reference_name
	reference_path.write_bytes(reference_bytes)
	monkeypatch.setitem(photopanda.STYLE_REFERENCE_PATHS, style, reference_path)
	observed = {}

	async def mock_provider(request: httpx.Request) -> httpx.Response:
		body = await request.aread()
		if request.method == 'POST':
			observed['request'] = request
			observed['body'] = body
			assert request.url == httpx.URL(PROMPT_EDIT_ENDPOINT)
			assert request.headers['X-API-Key'] == 'test-key'
			assert b'name="file"' in body
			assert f'filename="{source_filename}"'.encode() in body
			assert b'name="reference"' in body
			assert f'filename="{reference_name}"'.encode() in body
			assert SOURCE_BYTES in body
			assert reference_bytes in body
			assert b'name="operation"' in body and b'prompt_edit' in body
			assert b'name="prompt"' in body and STYLE_PROMPT.encode() in body
			assert b'gpt-image-2-medium' in body and b'1K' in body
			return httpx.Response(200, json={
				'id': str(uuid.uuid4()),
				'status': 'done',
				'type': 'prompt_edit',
				'outputUrl': 'https://photopanda.ru/files/result.png',
				'durationMs': 2468,
			}, request=request)

		assert request.method == 'GET'
		assert request.url == httpx.URL('https://photopanda.ru/files/result.png')
		return httpx.Response(200, content=OUTPUT_BYTES, headers={'content-type': 'image/png'}, request=request)

	async def run():
		async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
			return await photopanda.generate_doll_illustration(
				source_filename,
				style,
				settings=_settings(),
				client=client,
			)

	result = asyncio.run(run())
	assert result.image_bytes == OUTPUT_BYTES
	assert result.content_type == 'image/png'
	assert result.model_id == 'gpt-image-2-medium'
	assert result.resolution == '1K'
	assert result.attempts == 1
	assert len(observed) == 2


def test_photo_edit_sends_multiple_reference_images(image_storage, monkeypatch):
	_, source_filename = image_storage
	refs = [
		(image_storage[0] / 'style-1.png', PNG_SIGNATURE + b'reference-1'),
		(image_storage[0] / 'style-2.png', PNG_SIGNATURE + b'reference-2'),
		(image_storage[0] / 'style-3.png', PNG_SIGNATURE + b'reference-3'),
	]
	for path, data in refs:
		path.write_bytes(data)
	monkeypatch.setitem(photopanda.STYLE_REFERENCE_PATHS, 'bratz', [path for path, _ in refs])

	async def mock_provider(request: httpx.Request) -> httpx.Response:
		if request.method == 'POST':
			body = await request.aread()
			assert body.count(b'name="reference"') == 3
			for path, data in refs:
				assert f'filename="{path.name}"'.encode() in body
				assert data in body
			return httpx.Response(200, json={
				'id': str(uuid.uuid4()),
				'status': 'done',
				'type': 'prompt_edit',
				'outputUrl': 'https://photopanda.ru/files/result.png',
			}, request=request)
		assert request.method == 'GET'
		return httpx.Response(200, content=OUTPUT_BYTES, headers={'content-type': 'image/png'}, request=request)

	async def run():
		async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
			return await photopanda.generate_doll_illustration(
				source_filename,
				'bratz',
				settings=_settings(),
				client=client,
			)

	result = asyncio.run(run())
	assert result.image_bytes == OUTPUT_BYTES
	assert result.content_type == 'image/png'


def test_same_prompt_is_used_for_both_styles():
    assert STYLE_PROMPT == photopanda.STYLE_PROMPT


def test_missing_photo_panda_key_fails_without_request(image_storage):
	_, source_filename = image_storage
	requests_seen = []

	async def mock_provider(request: httpx.Request) -> httpx.Response:
		requests_seen.append(request)
		return httpx.Response(500, request=request)

	async def run():
		async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
			return await photopanda.generate_doll_illustration(
				source_filename,
				'bratz',
				settings=PhotoPandaSettings(api_key='', model_id='gpt-image-2-medium', resolution='1K'),
				client=client,
			)

	with pytest.raises(HTTPException) as error:
		asyncio.run(run())
	assert error.value.status_code == 503
	assert requests_seen == []


def test_missing_style_reference_fails_before_provider_request(image_storage, monkeypatch):
	_, source_filename = image_storage
	missing_path = image_storage[0] / 'not-added.png'
	monkeypatch.setitem(photopanda.STYLE_REFERENCE_PATHS, 'bratz', missing_path)
	requests_seen = []

	async def mock_provider(request: httpx.Request) -> httpx.Response:
		requests_seen.append(request)
		return httpx.Response(500, request=request)

	async def run():
		async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
			return await photopanda.generate_doll_illustration(source_filename, 'bratz', settings=_settings(), client=client)

	with pytest.raises(HTTPException) as error:
		asyncio.run(run())
	assert error.value.status_code == 503
	assert requests_seen == []


@pytest.mark.parametrize(('provider_status', 'expected_status'), [(401, 502), (402, 402), (429, 429), (503, 503)])
def test_provider_errors_are_mapped_without_body_leaks(provider_status, expected_status, image_storage, monkeypatch):
	_, source_filename = image_storage
	reference = image_storage[0] / 'style.png'
	reference.write_bytes(PNG_SIGNATURE + b'reference')
	monkeypatch.setitem(photopanda.STYLE_REFERENCE_PATHS, 'bratz', reference)

	async def mock_provider(request: httpx.Request) -> httpx.Response:
		return httpx.Response(provider_status, text='private provider response body; never expose', request=request)

	async def run():
		async with httpx.AsyncClient(transport=httpx.MockTransport(mock_provider)) as client:
			return await photopanda.generate_doll_illustration(source_filename, 'bratz', settings=_settings(), client=client)

	with pytest.raises(HTTPException) as error:
		asyncio.run(run())
	assert error.value.status_code == expected_status
	assert 'private provider response body' not in error.value.detail


def test_timeout_and_invalid_download_are_reported(image_storage, monkeypatch):
	_, source_filename = image_storage
	reference = image_storage[0] / 'style.png'
	reference.write_bytes(PNG_SIGNATURE + b'reference')
	monkeypatch.setitem(photopanda.STYLE_REFERENCE_PATHS, 'bratz', reference)

	async def timeout_transport(request: httpx.Request) -> httpx.Response:
		raise httpx.ReadTimeout('provider timeout', request=request)

	async def run_timeout():
		async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_transport)) as client:
			return await photopanda.generate_doll_illustration(source_filename, 'bratz', settings=_settings(), client=client)

	with pytest.raises(HTTPException) as timeout_error:
		asyncio.run(run_timeout())
	assert timeout_error.value.status_code == 504

	async def invalid_download(request: httpx.Request) -> httpx.Response:
		if request.method == 'POST':
			return httpx.Response(200, json={'status': 'done', 'outputUrl': 'https://photopanda.ru/files/out.png'}, request=request)
		return httpx.Response(200, content=b'not an image', headers={'content-type': 'image/png'}, request=request)

	async def run_invalid_output():
		async with httpx.AsyncClient(transport=httpx.MockTransport(invalid_download)) as client:
			return await photopanda.generate_doll_illustration(source_filename, 'bratz', settings=_settings(), client=client)

	with pytest.raises(HTTPException) as output_error:
		asyncio.run(run_invalid_output())
	assert output_error.value.status_code == 502
