"""/cases."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from case_workspace.telegram_bot import api_client
from case_workspace.telegram_bot.api_client import ApiError
from case_workspace.telegram_bot.keyboards.main import cases_list

router = Router()


@router.message(Command("cases"))
@router.message(F.text == "📁 Мои дела")
async def cmd_cases(message: Message, api_token: str) -> None:
    try:
        cases = api_client.list_cases(api_token)
    except ApiError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    if not cases:
        await message.answer("📭 Дел нет.")
        return
    lines = [f"📁 <b>Всего дел: {len(cases)}</b>\n"]
    for c in cases[:20]:
        d = c.get("days_left")
        mark = "🔴" if d is not None and d < 0 else ("🟡" if d is not None and d <= 14 else "🟢")
        lines.append(f"{mark} {c.get('case_number') or '—'} · {c.get('article') or '—'} — {d} дн.")
    await message.answer("\n".join(lines), parse_mode="HTML")
    await message.answer("Выберите дело:", reply_markup=cases_list(cases))


@router.callback_query(F.data.startswith("case:"))
async def on_case(cb: CallbackQuery, api_token: str) -> None:
    if cb.data is None:
        return
    try:
        case_id = int(cb.data.split(":", 1)[1])
    except ValueError:
        await cb.answer()
        return
    try:
        cases = api_client.list_cases(api_token)
    except ApiError as exc:
        await cb.answer(str(exc), show_alert=True)
        return
    case = next((c for c in cases if c["id"] == case_id), None)
    if case is None or not case.get("case_number"):
        await cb.answer("Дело не найдено", show_alert=True)
        return
    try:
        d = api_client.get_case(api_token, case["case_number"])
    except ApiError as exc:
        await cb.answer(str(exc), show_alert=True)
        return
    lines = [
        f"📁 <b>Дело {d['case_number']}</b>",
        f"Статья: {d.get('article') or '—'}",
        f"Возбуждено: {d.get('initiated_at') or '—'}",
        f"Срок: {d.get('current_deadline') or '—'}",
        f"Осталось: {d.get('days_left')} дн.",
    ]
    if d.get("accused_name"):
        lines.append(f"Обвиняемый: {d['accused_name']}")
    await cb.message.answer("\n".join(lines), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer()
