import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
load_dotenv(BACKEND_ROOT / '.env', override=False)

PROMPT_EDIT_ENDPOINT = 'https://photopanda.ru/api/v1/v1/photos/process'
REQUEST_TIMEOUT_SECONDS = 180
MAX_INPUT_SIZE_BYTES = 10 * 1024 * 1024
MAX_OUTPUT_SIZE_BYTES = 25 * 1024 * 1024

STYLE_REFERENCE_PATHS = {
    'bratz': PROJECT_ROOT / 'assets' / 'doll-style-reference.png',
    'monster_high': PROJECT_ROOT / 'assets' / 'monster-high-style-reference.png',
}

STYLE_PROMPT = '''Полностью перерисуй девушку с первого изображения в художественном стиле второго.

Первое фото — источник внешности, узнаваемых черт, позы, прически, одежды и композиции. Второе — обязательный референс стиля.

Не накладывай фильтр на фотографию. Создай полноценную иллюстрацию с нуля, изменив формы, линии, пропорции и способ изображения человека.

Максимально точно передай стиль второго изображения: стилизацию лица и глаз, формы носа и губ, прорисовку волос и одежды, характер линий, цветовую палитру, тени, свет, объём, детализацию и настроение.

Полностью замени фотографические текстуры и реалистичные детали их художественным изображением. Все элементы должны выглядеть как единая иллюстрация, нарисованная художником.

Сохрани узнаваемость девушки с первого фото. Не копируй внешность персонажа со второго изображения.

Первое изображение — внешность и композиция. Второе — стиль, формы и манера рисовки.'''


@dataclass(frozen=True)
class PhotoPandaSettings:
    api_key: str
    model_id: str
    resolution: str

    @classmethod
    def from_environment(cls) -> 'PhotoPandaSettings':
        return cls(
            api_key=os.getenv('PHOTOPANDA_API_KEY', '').strip(),
            model_id=os.getenv('PHOTOPANDA_MODEL_ID', 'gpt-image-2-medium').strip(),
            resolution=os.getenv('PHOTOPANDA_RESOLUTION', '1K').strip(),
        )
