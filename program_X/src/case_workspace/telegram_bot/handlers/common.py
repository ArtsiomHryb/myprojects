"""Статус / Выйти."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

router = Router()


@router.message(F.text == "📊 Статус")
async def cmd_status(message: Message, api_token: str) -> None:
    await message.answer(
        "📊 <b>Статус</b>\n\n✅ Авторизован",
        parse_mode="HTML",
    )


@router.message(F.text == "🚪 Выйти")
async def cmd_exit(message: Message) -> None:
    await message.answer("Используйте /logout для выхода.")
