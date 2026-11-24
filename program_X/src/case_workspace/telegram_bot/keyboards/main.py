"""Клавиатуры."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Мои дела"), KeyboardButton(text="⏰ Сроки")],
            [KeyboardButton(text="📊 Статус"), KeyboardButton(text="🚪 Выйти")],
        ],
        resize_keyboard=True,
    )


def cases_list(cases: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for c in cases[:20]:
        label = c.get("case_number") or "—"
        if c.get("article"):
            label += f" · {c['article']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"case:{c['id']}")])
    if not rows:
        rows = [[InlineKeyboardButton(text="Пусто", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)
