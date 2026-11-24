"""Запуск бота: python -m case_workspace.telegram_bot"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from case_workspace.logging_setup import setup_logging
from case_workspace.telegram_bot.bot import create_bot_and_dispatcher
from case_workspace.telegram_bot.config import load_bot_token


async def _run() -> None:
    token = load_bot_token()
    if not token:
        print(
            "ОШИБКА: токен бота не найден.\n"
            "Создайте файл ~/Library/Application Support/case_workspace/bot_token.txt "
            "или установите CASE_WORKSPACE_BOT_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)
    bot, dp = create_bot_and_dispatcher(token)
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    setup_logging()
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("Бот остановлен")


if __name__ == "__main__":
    main()
