import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from redis import Redis
from rq import Connection, Worker

from core.settings import get_settings
from storage.database import init_db


def main():
    settings = get_settings()
    settings.ensure_data_dirs()
    init_db()

    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker([settings.rq_queue_name])
        print(f"Worker started. Queue: {settings.rq_queue_name}")
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
