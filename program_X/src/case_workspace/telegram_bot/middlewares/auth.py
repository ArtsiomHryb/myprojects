"""Middleware авторизации."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from case_workspace.telegram_bot.session import sessions

PUBLIC = ("/start", "/help", "/logout")


class AuthRequiredMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        text = ""
        if isinstance(event, Message) and event.text:
            text = event.text.strip()
        elif isinstance(event, CallbackQuery) and event.data:
            text = event.data

        if any(text.startswith(c) for c in PUBLIC):
            return await handler(event, data)

        state = data.get("state")
        if state is not None:
            cur = await state.get_state()
            if cur == "AuthStates:waiting_password":
                return await handler(event, data)

        user = getattr(event, "from_user", None)
        if user is None:
            return None

        token = sessions.get(user.id)
        if token is None:
            if isinstance(event, Message):
                await event.answer("🔐 Введите /start для входа.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Требуется авторизация", show_alert=True)
            return None

        data["api_token"] = token
        return await handler(event, data)
