# Деплой на VPS без Docker (venv + systemd)

Docker для дипломного проекта **не обязателен**. На VPS достаточно:
- Python 3.10+ в виртуальном окружении
- PostgreSQL
- Redis
- systemd для автозапуска API и worker

## 1. Подготовка сервера (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  postgresql redis-server nginx git
```

## 2. PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE USER helmet WITH PASSWORD 'your_strong_password';
CREATE DATABASE helmet_db OWNER helmet;
\q
```

## 3. Клонирование и venv

```bash
sudo mkdir -p /opt/helmet_violation_system
sudo chown $USER:$USER /opt/helmet_violation_system
cd /opt/helmet_violation_system
git clone <your-repo-url> .

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Скопируйте веса модели на сервер:
`runs/helmet_detector/weights/best.pt`

## 4. Конфигурация

```bash
cp .env.example .env
nano .env
```

Пример для VPS:

```env
DATABASE_URL=postgresql://helmet:your_strong_password@127.0.0.1:5432/helmet_db
REDIS_URL=redis://127.0.0.1:6379/0
API_HOST=0.0.0.0
API_PORT=8000
API_PUBLIC_URL=http://YOUR_VPS_IP:8000
DATA_DIR=/opt/helmet_violation_system/data
INLINE_WORKER=false
```

Инициализация БД:

```bash
python scripts/init_db.py
```

## 5. systemd — API

Файл `/etc/systemd/system/helmet-api.service`:

```ini
[Unit]
Description=Helmet Violation API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/helmet_violation_system
EnvironmentFile=/opt/helmet_violation_system/.env
ExecStart=/opt/helmet_violation_system/.venv/bin/python scripts/run_api.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 6. systemd — Worker (инференс на VPS)

Файл `/etc/systemd/system/helmet-worker.service`:

```ini
[Unit]
Description=Helmet Violation RQ Worker
After=network.target redis.service helmet-api.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/helmet_violation_system
EnvironmentFile=/opt/helmet_violation_system/.env
ExecStart=/opt/helmet_violation_system/.venv/bin/python workers/run_worker.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable helmet-api helmet-worker
sudo systemctl start helmet-api helmet-worker
sudo systemctl status helmet-api helmet-worker
```

Проверка: `curl http://127.0.0.1:8000/health`

## 7. Nginx (опционально, HTTPS)

См. `deploy/nginx.conf.example`. Проксирует `/` на API `:8000`.

Streamlit можно запускать **локально на ПК**, указав `HELMET_API_URL=http://VPS_IP:8000`.

## 8. Локальная разработка (Windows, без Redis)

В `.env`:

```env
DATABASE_URL=sqlite:///./data/helmet.db
INLINE_WORKER=true
```

Терминал 1: `python scripts/run_api.py`  
Терминал 2: `python main.py` (Streamlit)

Worker отдельно не нужен — задачи выполняются в фоновом потоке API.

## Когда имеет смысл Docker?

- Несколько серверов с одинаковым окружением
- CI/CD с контейнерами

Для одного VPS и диплома **venv проще**: меньше слоёв, проще показать на защите `systemctl status` и логи.
