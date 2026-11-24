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
- проверка связи React ↔ FastAPI;
- сохранение гостевых проектов, настроек и metadata файлов в SQLite;
- приватное локальное project file storage;
- журнал синхронных задач генерации.

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

Для удаления фона нужен Python 3.11–3.13 (проверен Python 3.12). Существующее окружение Python 3.14 можно сохранить отдельно:

```bash
cd backend
python3.12 -m venv .venv-bg
source .venv-bg/bin/activate
pip install -r requirements.txt
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

## Проекты и локальное хранилище

SQLite используется через стандартный модуль `sqlite3`, без второго ORM. При старте backend применяет версионируемые SQL migrations и создаёт `backend/data/projects.sqlite3`. Таблицы `projects`, `assets`, `generation_tasks` и `packaging_templates` описаны в [ERD](docs/database/ERD.md). Таблица `users` подготовлена для будущего владельца проектов, но регистрация и авторизация сейчас не реализованы.

Создайте `backend/.env` из `backend/.env.example`. `DATABASE_PATH` задаёт файл базы, `FILE_STORAGE_ROOT` — корень файлового хранилища. Относительные пути задаются относительно `backend/`; абсолютные пути тоже допустимы. По умолчанию файлы размещаются в `backend/storage/projects/<project_uuid>/{originals,generated,processed,logos,previews,exports,intermediate}/`. Имена генерируются случайно, исходное имя не используется как путь. БД и storage исключены из Git.

При запуске frontend создаётся гостевой проект. В `localStorage` браузера сохраняется случайный capability token; в БД находится только его SHA-256 hash. Токен передаётся в `X-Guest-Token`, защищает чтение/изменение проекта и выдачу assets. Утерянный токен восстановить нельзя. Позже проект можно связать с `users.id`, сохранив project UUID и assets.

Пользовательские внешние/внутренние фоны сохраняются отдельными файлами типа `intermediate` с metadata `slot`; в `settings_json` остаётся только ID asset, не изображение и не base64 data URL. Логотип и фото также сохраняются как assets.

Текущие project endpoints:

- `POST /api/projects` — создать проект, вернуть проект и гостевой token (показывается один раз);
- `GET /api/projects/{id}` — получить настройки, assets и задачи по token;
- `PATCH /api/projects/{id}` — сохранить персонализацию;
- `DELETE /api/projects/{id}` — удалить проект и его файлы;
- `POST /api/projects/{id}/assets` — загрузить asset с `asset_type`;
- `GET /api/projects/{id}/assets/{asset_id}/content` — приватно получить файл;
- `DELETE /api/projects/{id}/assets/{asset_id}` — удалить asset;
- `POST /api/images/generate` сохраняет task и generated assets, если переданы `project_id` и `guest_token`. Вызовы без них сохраняют старый контракт.

Генерация PhotoPanda и удаление фона сейчас синхронны в рамках HTTP-запроса. `generation_tasks` фиксирует `running` → `succeeded`/`failed`, но отдельной очереди фоновых workers пока нет. Превью сборки и PDF export ещё не реализованы, поэтому соответствующие типы assets/templates зарезервированы в схеме. Старый совместимый endpoint `/uploads/images` всё ещё обслуживает прежние одиночные upload/generation вызовы; новые project assets не публикуются там.

Тесты backend: из папки `backend/` выполните `python -m pytest tests -q` в окружении, установленном из `requirements.txt`.

## Миграции и резервные копии

Миграции хранятся в `backend/app/db/database.py` как последовательные SQL-версии и автоматически применяются при старте backend. Каждая версия и её SQL выполняются в одной явной SQLite-транзакции; применённые номера записаны в `schema_migrations`. Для нового изменения схемы добавляйте новую запись в список `MIGRATIONS`, не редактируйте уже опубликованные migration scripts. Перед обновлением сделайте backup.

Ручные команды из каталога `backend/` (Python 3.12 environment):

```bash
source .venv-bg/bin/activate
python backup.py create
python backup.py verify ~/Library/Application\ Support/DollPackaging/backups/doll-packaging-YYYYMMDDTHHMMSSffffffZ.zip
python retention.py ~/Library/Application\ Support/DollPackaging/backups --keep 7
python retention.py ~/Library/Application\ Support/DollPackaging/backups --keep 7 --apply
```

Retention без `--apply` только показывает план и ничего не удаляет. С `--apply` он сначала создаёт новый ZIP, проверяет SHA-256 каждого файла, SQLite `integrity_check` и `foreign_key_check`, и лишь затем удаляет старые проверенные копии. Повреждённые или неизвестные ZIP он сохраняет. Поддержана GFS политика:

```bash
python retention.py ~/Library/Application\ Support/DollPackaging/backups --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --apply
```

Архив включает согласованный online snapshot SQLite, `backend/storage/projects/` и legacy `backend/uploads/images/`. ZIP публикуется атомарно только после проверки. Для скачивания активных проектов система получает общий lock на время архивации и изменений файлов. По умолчанию локальная команда складывает архивы в игнорируемый `backend/backups/`; перед production настройте `BACKUP_ROOT` на отдельный диск или защищённое удалённое хранилище. Локальный backup на том же диске не защищает от поломки/потери компьютера. В архив входят пользовательские фотографии и PDF, поэтому храните его приватно и зашифруйте внешний диск/удалённую копию.

На macOS установите ежедневное расписание (03:15, 7 дневных + 4 недельных + 3 месячных):

```bash
cd backend
source .venv-bg/bin/activate
python install_backup_schedule.py install
```

LaunchAgent создаёт копии в `~/Library/Application Support/DollPackaging/backups`; вывод и ошибки находятся в подпапке `logs`. Удалить расписание можно командой `python install_backup_schedule.py uninstall`. После установки рекомендуется один раз проверить результат через `python backup.py verify <archive.zip>`.

## AI-модуль PhotoPanda

AI-интеграция изолирована в `backend/app/services/ai/photopanda.py` и `backend/app/services/ai/config.py`. FastAPI route только передаёт сохранённый UUID исходного изображения и выбранный стиль сервису; ключ, prompt и пути reference-файлов frontend не получает. Результат сохраняется через существующий image storage и возвращается с URL для preview.

Текущая конфигурация reference-файлов:

- Bratz: `assets/bratzReference1.png`, `assets/bratzReference2.png`, `assets/bratzReference3.png`.
- Monster High: `assets/monsterhighreference1.png`, `assets/monsterhighReference2.png`, `assets/monsterhighReference3.png`.

Пути задаются в `backend/app/services/ai/config.py`; это локальные ресурсы проекта, не загружаемые пользователем при каждом запросе. Если reference выбранного стиля отсутствует, backend возвращает configuration error и не обращается к PhotoPanda.

Создайте `backend/.env` на основе `backend/.env.example` и добавьте ключ:

```env
PHOTOPANDA_API_KEY=ваш_ключ
PHOTOPANDA_MODEL_ID=gpt-image-2-medium
PHOTOPANDA_RESOLUTION=1K
```

`backend/.env` игнорируется Git. API key остаётся только на backend. Конфигурация по умолчанию: `gpt-image-2-medium`, `1K`; разрешённые варианты модели и разрешения описаны в `config.py`.

PhotoPanda получает `POST https://photopanda.ru/api/v1/v1/photos/process` с `operation=prompt_edit`, одним `file` (исходное фото), полями `reference` (стиль), общим `prompt`, `modelId` и `resolution`. Prompt общий для обоих стилей; различается только reference. При успехе backend скачивает `outputUrl`, проверяет signature/MIME и размер до 25 МБ, затем сохраняет файл в `backend/uploads/images/`. Загрузки и генерации продолжают использовать уже существующую проверку исходного фото JPG/JPEG/PNG до 10 МБ.

Для Monster High результат дополнительно обрабатывается локально с помощью `rembg` и модели `isnet-general-use`. Модель загружается автоматически при первом запросе (около 180 МБ, необходим интернет) и затем используется из локального кеша. Перед запросом к PhotoPanda backend проверяет, что модель доступна. Сохраняются исходный результат и PNG с альфа-каналом, обрезанный по границам маски; API возвращает URL PNG и его `width` и `height`. При ошибке обработки в сообщении указан URL сохранённого исходника. Сегментация может сохранять остатки фона или обрезать тонкие детали, поэтому результат следует визуально проверять. Для коммерческого использования проверьте лицензию весов модели.

Пользовательские фотографии, результаты генерации и тестовый файл не следует добавлять в Git. Изображения в `backend/uploads/images/` остаются на диске до их ручного удаления.

Установка и запуск:

```bash
cd backend
source .venv-bg/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

В существующем frontend загрузите исходное фото, выберите Bratz или Monster High, перейдите на «Создать по фото» и запустите генерацию. Повтор доступен вручную; автоматических повторов нет. Результат отображается в текущем preview-сценарии. Для запуска тестов используйте `python -m pytest backend/tests` из корня репозитория или `pytest -q` из `backend/`; тесты мокируют весь PhotoPanda HTTP-трафик и не расходуют баланс.
