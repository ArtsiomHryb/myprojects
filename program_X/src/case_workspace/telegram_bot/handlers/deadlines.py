"""/deadlines."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from case_workspace.telegram_bot import api_client
from case_workspace.telegram_bot.api_client import ApiError

router = Router()


@router.message(Command("deadlines"))
@router.message(F.text == "⏰ Сроки")
async def cmd_deadlines(message: Message, api_token: str) -> None:
    try:
        items = api_client.list_deadlines(api_token, days=30)
    except ApiError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    if not items:
        await message.answer("✅ В ближайшие 30 дней сроков нет.")
        return
    lines = ["⏰ <b>Ближайшие 30 дней:</b>\n"]
    for it in items:
        d = it["days_left"]
        mark = "🔴" if d < 0 else ("🟡" if d <= 14 else "🟢")
        lines.append(f"{mark} {it.get('case_number') or '—'} — до {it['current_deadline']}, {d} дн.")
    await message.answer("\n".join(lines), parse_mode="HTML")
