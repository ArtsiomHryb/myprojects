"""Инициализация БД."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from case_workspace.config import DB_PATH
from case_workspace.db.models import Base

# Регистрируем все модели в Base.metadata до create_all
from case_workspace.projects import models as _projects  # noqa: F401,E402
from case_workspace.participants import models as _participants  # noqa: F401,E402
from case_workspace.identifiers import models as _identifiers  # noqa: F401,E402
from case_workspace.crypto import models as _crypto  # noqa: F401,E402
from case_workspace.templates import models as _templates  # noqa: F401,E402
from case_workspace.documents import models as _documents  # noqa: F401,E402
from case_workspace.legal import models as _legal  # noqa: F401,E402
from case_workspace.inbox import models as _inbox  # noqa: F401,E402
from case_workspace.timetracking import models as _time  # noqa: F401,E402
from case_workspace.calendar import models as _cal  # noqa: F401,E402


def init_db() -> Engine:
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
    Base.metadata.create_all(engine)
    # Заполняем встроенные справочники (idempotent)
    from case_workspace.identifiers.local import seed_local_tables

    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        seed_local_tables(s)
    return engine


def session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)