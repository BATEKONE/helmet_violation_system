# Система детекции нарушений — отсутствие шлема у мотоциклистов

Дипломный проект: YOLOv8, трекинг, temporal filter, **сервисная архитектура** (API + очередь + worker + БД).

## Архитектура

```
Streamlit (UI)  ──HTTP──►  FastAPI (API)  ──►  PostgreSQL / SQLite
                                │
                                ▼
                            Redis (RQ)
                                │
                                ▼
                         Worker (ML pipeline)
                                │
                         data/jobs/{id}/
```

- **`core/`** — ML pipeline (без HTTP)
- **`api/`** — REST API
- **`workers/`** — фоновая обработка видео
- **`storage/`** — БД и файлы задач
- **`services/`** — бизнес-логика задач
- **`ui/`** — Streamlit-клиент к API

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
```

## Локальный запуск (без Redis)

В `.env`:

```env
DATABASE_URL=sqlite:///./data/helmet.db
INLINE_WORKER=true
```

```bash
python scripts/init_db.py
python scripts/run_api.py
```

В другом терминале:

```bash
set HELMET_API_URL=http://127.0.0.1:8000
python main.py
```

## VPS (без Docker)

Подробно: **[deploy/DEPLOY.md](deploy/DEPLOY.md)**

Кратко:
1. PostgreSQL + Redis на сервере
2. Python 3.10: `bash deploy/setup_venv_pyenv.sh` (см. [deploy/DEPLOY.md](deploy/DEPLOY.md))
3. `.env` с `DATABASE_URL=postgresql://...`, `INLINE_WORKER=false`
4. systemd: `helmet-api.service`, `helmet-worker.service`

Streamlit на ПК:

```bash
set HELMET_API_URL=http://IP_ВАШЕГО_VPS:8000
python main.py
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Статус API, БД, Redis |
| POST | `/api/v1/jobs` | Загрузка видео |
| GET | `/api/v1/jobs/{id}` | Статус задачи |
| GET | `/api/v1/jobs/{id}/events` | Нарушения |
| GET | `/api/v1/jobs/{id}/video` | Обработанное видео |
| GET | `/api/v1/events/{id}/image` | Снимок нарушения |

Документация: http://localhost:8000/docs

## Обучение модели

```bash
python training/train_yolo.py --epochs 50 --device 0
```

Веса: `runs/helmet_detector/weights/best.pt` (скопировать на VPS).

## CLI (без API)

```bash
python inference/infer_video.py --source video.mp4 --output outputs/result.mp4
```

События сохраняются в `events/` (файловый режим).

## Структура проекта

```
helmet_violation_system/
├── api/              # FastAPI
├── core/             # ML pipeline
├── services/         # Use-cases
├── storage/          # БД, репозитории
├── workers/          # RQ worker
├── ui/               # Streamlit + api_client
├── scripts/          # run_api, init_db
├── deploy/           # systemd, nginx, DEPLOY.md
├── data/             # uploads, jobs (gitignore)
└── inference/        # CLI
```

## Технологии

Python 3.10+, PyTorch, YOLOv8, FastAPI, SQLAlchemy, Redis, RQ, Streamlit
