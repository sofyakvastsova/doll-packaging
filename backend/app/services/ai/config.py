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


def _resolve_style_reference_paths(style: str) -> list[Path]:
    candidates = {
        'bratz': [
            'bratzReference1.png',
            'bratzReference2.png',
            'bratzReference3.png',
            'doll-style-reference.png',
        ],
        'monster_high': [
            'monster-high-style-reference.png',
            'monsterHighReference1.png',
            'monster-high-reference.png',
        ],
    }

    resolved: list[Path] = []
    for name in candidates.get(style, []):
        path = PROJECT_ROOT / 'assets' / name
        if path.exists():
            resolved.append(path)
    return resolved


STYLE_REFERENCE_PATHS = {
    'bratz': _resolve_style_reference_paths('bratz'),
    'monster_high': _resolve_style_reference_paths('monster_high'),
}

STYLE_PROMPT = '''Transform the girl in image 1 into a full-body artwork matching the artistic language of images 2–4. Study and replicate their proportions, shapes, linework and hand-drawn texture. Exaggerate the anatomy: the head and legs must be much larger relative to the short, small torso. Do not use realistic human proportions; follow the references even if the result looks deliberately stylized or anatomically unusual. Keep her recognizable face, hairstyle, outfit and defining details. Use visible strokes, loose sketchy lines, irregular contours and imperfect color fills. Hair should be simplified and schematic, built from curls and directional strokes rather than finely rendered individual hairs. Avoid smooth gradients, flawless surfaces, uniform coloring and excessive digital polish. The result should look genuinely hand-drawn, not like a filtered photo or generic AI art. Show the complete figure from head to toe. Image 1 is the character reference; images 2–4 are the style and proportion
'''


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
