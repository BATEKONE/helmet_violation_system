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

## 3. Клонирование и venv (Python 3.10)

Рекомендуется **Python 3.10.14** (файл `.python-version` в корне репозитория для pyenv).

```bash
sudo mkdir -p /opt/helmet_violation_system
sudo chown $USER:$USER /opt/helmet_violation_system
cd /opt/helmet_violation_system
git clone <your-repo-url> .
```

### Вариант A: pyenv (Debian / когда `apt` не находит python3.10)

Ошибка `pyenv: python: command not found` значит, что 3.10 установлен, но **не выбран**
в каталоге проекта. Не используйте голый `python3 -m venv` — часто это системный 3.11/3.12.

**Один раз — установка pyenv и Python 3.10.14:**

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev curl llvm libncursesw5-dev xz-utils \
  tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git

curl https://pyenv.run | bash
# Добавьте в ~/.bashrc (для root: /root/.bashrc):
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
source ~/.bashrc
```

**Создание venv (автоматически):**

```bash
cd /opt/helmet_violation_system
bash deploy/setup_venv_pyenv.sh
```

Скрипт выполняет: `pyenv local 3.10.14` → `python -m venv .venv` → проверка версии → `pip install`.

На VPS **без GPU**, если `torch` не ставится:

```bash
INSTALL_TORCH_CPU=1 bash deploy/setup_venv_pyenv.sh
```

**Вручную (если скрипт не нужен):**

```bash
cd /opt/helmet_violation_system
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv local 3.10.14
python --version          # Python 3.10.14
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
python --version          # снова 3.10.14 — обязательно!
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Проверка после `python3 -m venv` (если уже создавали venv раньше):

```bash
.venv/bin/python --version
# если не 3.10.14 — rm -rf .venv и повторите шаги выше
```

### Вариант B: Ubuntu + deadsnakes (если PPA доступен)

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

cd /opt/helmet_violation_system
python3.10 -m venv .venv
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

Инициализация БД (из активированного venv или полным путём):

```bash
source .venv/bin/activate
python scripts/init_db.py
# или:
/opt/helmet_violation_system/.venv/bin/python scripts/init_db.py
```

**systemd** не читает `~/.bashrc` и pyenv — в unit-файлах только
`/opt/helmet_violation_system/.venv/bin/python` (см. `deploy/helmet-api.service`).

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
