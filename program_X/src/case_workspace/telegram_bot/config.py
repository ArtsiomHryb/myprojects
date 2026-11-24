"""Конфигурация бота."""

from __future__ import annotations

import os
from pathlib import Path

from case_workspace.config import DATA_DIR

BOT_TOKEN_FILE = DATA_DIR / "bot_token.txt"
API_URL = "http://127.0.0.1:8765/api/v1"


def load_bot_token() -> str | None:
    env_token = os.environ.get("CASE_WORKSPACE_BOT_TOKEN", "").strip()
    if env_token:
        return env_token
    if BOT_TOKEN_FILE.exists():
        try:
            return BOT_TOKEN_FILE.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None


def save_bot_token(token: str) -> None:
    BOT_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    BOT_TOKEN_FILE.write_text(token.strip(), encoding="utf-8")
