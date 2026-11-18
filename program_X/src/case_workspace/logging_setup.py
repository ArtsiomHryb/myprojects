"""Настройка логирования через loguru."""

import sys

from loguru import logger

from case_workspace.config import LOG_DIR


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )