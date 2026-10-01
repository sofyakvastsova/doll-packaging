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
