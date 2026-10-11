# Doll Packaging

Прототип веб-системы автоматизированного формирования персонализированной кукольной упаковки на основе пользовательских изображений.

## Описание

Это первый рабочий Prototype проекта для автоматического формирования упаковки. В текущем этапе реализованы:

- React frontend;
- базовый FastAPI backend;
- единый экран создания упаковки;
- загрузка изображения;
- выбор типа упаковки;
- выбор внешнего и внутреннего фона;
- загрузка логотипа;
- ввод имени и описания;
- живой frontend-предпросмотр;
- проверка связи React ↔ FastAPI.

## Технологии

- React 19 + Vite
- FastAPI
- Uvicorn
- CSS Modules / обычный CSS

## Структура проекта

```text
.
├── README.md
├── assets/
├── backend/
│   ├── .venv/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── generated/
├── templates/
└── .gitignore
```

## Запуск frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Frontend будет доступен по адресу:

- http://localhost:5173

## Запуск backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend будет доступен по адресу:

- http://localhost:8000

Health endpoint:

- http://localhost:8000/api/health

## Проверка работоспособности

Проверить API можно через браузер или curl:

```bash
curl http://localhost:8000/api/health
```

Результат:

```json
{"status": "ok"}
```

## AI-модуль PhotoPanda

AI-интеграция изолирована в `backend/app/services/ai/photopanda.py` и `backend/app/services/ai/config.py`. FastAPI route только передаёт сохранённый UUID исходного изображения и выбранный стиль сервису; ключ, prompt и пути reference-файлов frontend не получает. Результат сохраняется через существующий image storage и возвращается с URL для preview.

Текущая конфигурация reference-файлов:

- Bratz: `assets/doll-style-reference.png` (файл уже добавлен).
- Monster High: `assets/monster-high-style-reference.png` (файл нужно добавить отдельно).

Пути задаются в `backend/app/services/ai/config.py`; это локальные ресурсы проекта, не загружаемые пользователем при каждом запросе. Если reference выбранного стиля отсутствует, backend возвращает configuration error и не обращается к PhotoPanda.

Создайте `backend/.env` на основе `backend/.env.example` и добавьте ключ:

```env
PHOTOPANDA_API_KEY=ваш_ключ
PHOTOPANDA_MODEL_ID=gpt-image-2-medium
PHOTOPANDA_RESOLUTION=1K
```

`backend/.env` игнорируется Git. API key остаётся только на backend. Конфигурация по умолчанию: `gpt-image-2-medium`, `1K`; разрешённые варианты модели и разрешения описаны в `config.py`.

PhotoPanda получает `POST https://photopanda.ru/api/v1/v1/photos/process` с `operation=prompt_edit`, одним `file` (исходное фото), одним multipart `reference` (стиль), общим `prompt`, `modelId` и `resolution`. Prompt общий для обоих стилей; различается только reference. При успехе backend скачивает `outputUrl`, проверяет signature/MIME и размер до 25 МБ, затем сохраняет файл в `backend/uploads/images/`. Загрузки и генерации продолжают использовать уже существующую проверку исходного фото JPG/JPEG/PNG до 10 МБ.

Установка и запуск:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

В существующем frontend загрузите исходное фото, выберите Bratz или Monster High, перейдите на «Создать по фото» и запустите генерацию. Повтор доступен вручную; автоматических повторов нет. Результат отображается в текущем preview-сценарии. Для запуска тестов используйте `python -m pytest backend/tests` из корня репозитория или `pytest -q` из `backend/`; тесты мокируют весь PhotoPanda HTTP-трафик и не расходуют баланс.
