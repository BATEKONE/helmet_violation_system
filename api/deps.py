from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from storage.database import _get_session_factory, init_db

init_db()


def get_db() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
