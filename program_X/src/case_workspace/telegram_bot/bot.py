"""Сборка бота."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from case_workspace.telegram_bot.handlers import (
    auth, cases, common, deadlines, identifiers, start,
)
from case_workspace.telegram_bot.middlewares.auth import AuthRequiredMiddleware


def create_bot_and_dispatcher(token: str) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AuthRequiredMiddleware())
    dp.callback_query.middleware(AuthRequiredMiddleware())
    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(cases.router)
    dp.include_router(deadlines.router)
    dp.include_router(common.router)
    dp.include_router(identifiers.router)
    return bot, dp
