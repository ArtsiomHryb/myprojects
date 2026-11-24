"""Проверка идентификаторов."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from case_workspace.telegram_bot import api_client
from case_workspace.telegram_bot.api_client import ApiError

router = Router()

SKIP = {"📁 Мои дела", "⏰ Сроки", "📊 Статус", "🚪 Выйти"}


@router.message(F.text & ~F.text.startswith("/"))
async def on_any_text(message: Message, api_token: str) -> None:
    text = (message.text or "").strip()
    if not text or text in SKIP or len(text) > 200:
        return
    try:
        result = api_client.resolve_identifier(api_token, text)
    except ApiError as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    if result.get("error"):
        await message.answer(f"⚠️ {result['error']}")
        return
    labels = {"card": "💳 Карта", "iban": "🏦 IBAN", "phone": "📱 Телефон", "ip": "🌐 IP"}
    status = {
        "confirmed": "🟢 подтверждено",
        "partial": "🟡 частично",
        "conflict": "🔴 расхождение",
        "unknown": "⚪ неизвестно",
    }
    lines = [
        f"<b>{labels.get(result['type'], result['type'])}</b>",
        f"<code>{result['value']}</code>",
        f"Статус: {status.get(result['verification_status'], '')}",
    ]
    local = result.get("local")
    if local:
        lines.append("\n<b>Локально:</b>")
        if result["type"] in ("card", "iban"):
            lines.append(f"  Банк: {local.get('bank_name', '—')}")
        elif result["type"] == "phone":
            lines.append(f"  Оператор: {local.get('carrier', '—')}")
        elif result["type"] == "ip":
            lines.append(f"  {local.get('country', '')} {local.get('city', '')}".strip())
    online = result.get("online")
    if online:
        lines.append("\n<b>Онлайн:</b>")
        if result["type"] in ("card", "iban"):
            lines.append(f"  Банк: {online.get('bank_name', '—')}")
        elif result["type"] == "ip":
            lines.append(f"  {online.get('country', '')} {online.get('city', '')}".strip())
    await message.answer("\n".join(lines), parse_mode="HTML")
