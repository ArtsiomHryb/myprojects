"""Инициализация БД."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from case_workspace.config import DB_PATH
from case_workspace.db.models import Base

# Регистрируем все модели в Base.metadata до create_all
from case_workspace.projects import models as _projects  # noqa: F401,E402
from case_workspace.participants import models as _participants  # noqa: F401,E402


def init_db() -> Engine:
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
    Base.metadata.create_all(engine)
    return engine


def session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)