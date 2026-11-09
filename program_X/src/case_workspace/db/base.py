"""Инициализация БД."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from case_workspace.config import DB_PATH
from case_workspace.db.models import Base


def init_db() -> Engine:
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
    Base.metadata.create_all(engine)
    return engine


def session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)