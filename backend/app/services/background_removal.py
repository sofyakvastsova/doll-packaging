from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


class BackgroundRemovalError(Exception):
    pass


@dataclass(frozen=True)
class PreparedImage:
    png_bytes: bytes
    width: int
    height: int


@lru_cache(maxsize=1)
def _session():
    from rembg import new_session

    return new_session('isnet-general-use')


def initialize_background_removal() -> None:
    try:
        _session()
    except Exception as error:
        raise BackgroundRemovalError('Модель удаления фона недоступна.') from error


def _remove_background(image: Image.Image) -> Image.Image:
    from rembg import remove

    return remove(image, session=_session(), decontaminate=True)


def prepare_doll_image(image_bytes: bytes) -> PreparedImage:
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise BackgroundRemovalError('Изображение пустое или превышает допустимый размер.')

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            if source.format not in {'PNG', 'JPEG', 'WEBP'}:
                raise BackgroundRemovalError('Неподдерживаемый формат изображения.')
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise BackgroundRemovalError('Размер изображения в пикселях превышает допустимый.')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGBA')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise BackgroundRemovalError('Не удалось прочитать изображение.') from error

    try:
        cutout = _remove_background(image).convert('RGBA')
    except Exception as error:
        raise BackgroundRemovalError('Не удалось удалить фон изображения.') from error

    if cutout.size != image.size:
        raise BackgroundRemovalError('Размер результата удаления фона некорректен.')
    bounds = cutout.getchannel('A').point(lambda alpha: 255 if alpha > 8 else 0).getbbox()
    if bounds is None:
        raise BackgroundRemovalError('Не удалось найти куклу на изображении.')
    left, top, right, bottom = bounds
    cutout = cutout.crop((max(0, left - 4), max(0, top - 4), min(cutout.width, right + 4), min(cutout.height, bottom + 4)))
    output = BytesIO()
    cutout.save(output, format='PNG')
    return PreparedImage(output.getvalue(), cutout.width, cutout.height)