Вот красиво оформленный README.md файл, готовый для вставки в ваш проект:

```markdown
# 🏍️ Система детекции нарушений — отсутствие шлема у мотоциклистов

> Дипломный проект на основе YOLOv8, трекинга, temporal filter и сервисной архитектуры

## 📋 Оглавление

- [Архитектура](#-архитектура)
- [Установка](#-установка)
- [Локальный запуск](#-локальный-запуск-без-redis)
- [Деплой на VPS](#-vps-без-docker)
- [API](#-api)
- [Обучение модели](#-обучение-модели)
- [CLI](#-cli-без-api)
- [Настройка производительности](#-ускорение-обработки-на-сервере)
- [Технологии](#-технологии)
- [Структура проекта](#-структура-проекта)

## 🏗 Архитектура

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

### Компоненты системы

| Компонент | Описание |
|-----------|----------|
| `core/` | ML pipeline (без HTTP) |
| `api/` | REST API |
| `workers/` | Фоновая обработка видео |
| `storage/` | БД и файлы задач |
| `services/` | Бизнес-логика задач |
| `ui/` | Streamlit-клиент к API |

## 🚀 Установка

```bash
# Клонирование репозитория
git clone <your-repo-url>
cd helmet_violation_system

# Создание виртуального окружения
python -m venv .venv

# Активация окружения
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp .env.example .env
```

## 💻 Локальный запуск (без Redis)

### 1. Настройка `.env`

```env
DATABASE_URL=sqlite:///./data/helmet.db
INLINE_WORKER=true
```

### 2. Запуск сервера

```bash
# Инициализация базы данных
python scripts/init_db.py

# Запуск API сервера
python scripts/run_api.py
```

### 3. Запуск клиента

В другом терминале:

```bash
set HELMET_API_URL=http://127.0.0.1:8000   # Windows
export HELMET_API_URL=http://127.0.0.1:8000 # Linux/Mac

python main.py
```

## ☁️ VPS (без Docker)

> 📖 **Подробная инструкция**: [deploy/DEPLOY.md](deploy/DEPLOY.md)

### Краткий гайд:

1. **Установка зависимостей на сервере**
   ```bash
   sudo apt update
   sudo apt install postgresql redis-server
   ```

2. **Настройка окружения**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Конфигурация `.env`**
   ```env
   DATABASE_URL=postgresql://user:password@localhost/helmet_db
   INLINE_WORKER=false
   ```

4. **Запуск через systemd**
   ```bash
   sudo systemctl start helmet-api
   sudo systemctl start helmet-worker
   ```

### Запуск Streamlit клиента на локальном ПК

```bash
set HELMET_API_URL=http://IP_ВАШЕГО_VPS:8000   # Windows
export HELMET_API_URL=http://IP_ВАШЕГО_VPS:8000 # Linux/Mac

python main.py
```

## 📡 API

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Статус API, БД, Redis |
| `POST` | `/api/v1/jobs` | Загрузка видео |
| `GET` | `/api/v1/jobs/{id}` | Статус задачи |
| `GET` | `/api/v1/jobs/{id}/events` | Список нарушений |
| `GET` | `/api/v1/jobs/{id}/video` | Обработанное видео |
| `GET` | `/api/v1/events/{id}/image` | Снимок нарушения |

### Интерактивная документация

После запуска сервера откройте в браузере: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🧠 Обучение модели

```bash
# Запуск обучения YOLOv8
python training/train_yolo.py --epochs 50 --device 0
```

**Результаты**: `runs/helmet_detector/weights/best.pt`

> 💡 **Совет**: Скопируйте итоговые веса на VPS после обучения.

## 🎮 CLI (без API)

Для быстрого тестирования без развертывания API:

```bash
python inference/infer_video.py --source video.mp4 --output outputs/result.mp4
```

События нарушений сохраняются в папке `events/` (файловый режим).

## ⚡ Ускорение обработки на сервере

> **Важно**: После изменения параметров в `.env` перезапустите `helmet-api` и `helmet-worker`

### Основные параметры оптимизации

| Переменная | Эффект |
|------------|--------|
| `INFERENCE_DEVICE=0` | Использование GPU (максимальный прирост) |
| `PROCESS_EVERY_N_FRAMES=2` или `3` | Обработка не каждого кадра (~×2–×3 быстрее) |
| `INFERENCE_IMGSZ=416` | Уменьшение входного размера (~×1.5–×2 на CPU) |
| `INFERENCE_MAX_WIDTH=640` | Ресайз кадра перед детекцией |
| `EXPORT_ANNOTATED_VIDEO=false` | Отключение записи видео (очень быстро) |
| `VIDEO_WEB_OPTIMIZE=false` | Отключение ffmpeg в конце |
| `TORCH_NUM_THREADS=4` | Использование ядер CPU |

### Пример для слабого CPU VPS

```env
INFERENCE_DEVICE=cpu
INFERENCE_IMGSZ=416
INFERENCE_MAX_WIDTH=640
PROCESS_EVERY_N_FRAMES=3
EXPORT_ANNOTATED_VIDEO=true
VIDEO_WEB_OPTIMIZE=false
TORCH_NUM_THREADS=4
```

### Проверка GPU на сервере

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

## 📁 Структура проекта

```
helmet_violation_system/
├── api/              # FastAPI эндпоинты
├── core/             # ML pipeline ядро
├── services/         # Use-cases и бизнес-логика
├── storage/          # База данных и репозитории
├── workers/          # RQ воркеры
├── ui/               # Streamlit интерфейс + API клиент
├── scripts/          # Утилиты (run_api, init_db)
├── deploy/           # systemd, nginx, DEPLOY.md
├── data/             # uploads, jobs (в .gitignore)
├── inference/        # CLI инструменты
└── training/         # Обучение модели
```

## 🛠 Технологии

| Технология | Назначение |
|------------|------------|
| Python 3.10+ | Основной язык |
| PyTorch | Deep Learning фреймворк |
| YOLOv8 | Детекция объектов |
| FastAPI | REST API |
| SQLAlchemy | ORM |
| Redis / RQ | Очередь задач |
| Streamlit | Web интерфейс |

---

## 📝 Лицензия

Этот проект разработан в рамках дипломной работы.

---

**🐛 Баги и предложения**: [создать issue](your-repo-url/issues)
```
