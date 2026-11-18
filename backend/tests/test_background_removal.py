from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.services import background_removal


def image_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def test_prepares_rgba_and_preserves_white_details(monkeypatch):
    image = Image.new('RGBA', (100, 140), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 20, 69, 119), fill='black')
    draw.rectangle((40, 50, 59, 70), fill='white')

    def remove_background(source):
        mask = Image.new('L', source.size, 0)
        ImageDraw.Draw(mask).rectangle((30, 20, 69, 119), fill=255)
        source.putalpha(mask)
        return source

    monkeypatch.setattr(background_removal, '_remove_background', remove_background)
    result = background_removal.prepare_doll_image(image_bytes(image))
    output = Image.open(BytesIO(result.png_bytes))
    assert output.format == 'PNG'
    assert output.mode == 'RGBA'
    assert output.size == (48, 108) == (result.width, result.height)
    assert output.getpixel((0, 0))[3] == 0
    assert output.getpixel((14, 34)) == (255, 255, 255, 255)
    assert output.getchannel('A').getbbox() == (4, 4, 44, 104)


@pytest.mark.parametrize('content', [b'', b'not an image'])
def test_rejects_invalid_input(content):
    with pytest.raises(background_removal.BackgroundRemovalError):
        background_removal.prepare_doll_image(content)


def test_reports_segmentation_error(monkeypatch):
    def fail(_image):
        raise RuntimeError('model failure')

    monkeypatch.setattr(background_removal, '_remove_background', fail)
    with pytest.raises(background_removal.BackgroundRemovalError, match='удалить фон'):
        background_removal.prepare_doll_image(image_bytes(Image.new('RGB', (10, 10), 'white')))


def test_rejects_fully_transparent_result(monkeypatch):
    monkeypatch.setattr(background_removal, '_remove_background', lambda image: Image.new('RGBA', image.size))
    with pytest.raises(background_removal.BackgroundRemovalError, match='найти куклу'):
        background_removal.prepare_doll_image(image_bytes(Image.new('RGB', (10, 10), 'white')))