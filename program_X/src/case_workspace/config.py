"""Пути и константы приложения."""

from pathlib import Path

import platformdirs

APP_NAME = "case_workspace"
APP_AUTHOR = "case_workspace"

DATA_DIR: Path = Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR: Path = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH: Path = DATA_DIR / "case_workspace.db"