"""Ввод пароля и /logout."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from case_workspace.telegram_bot import api_client
from case_workspace.telegram_bot.api_client import ApiError
from case_workspace.telegram_bot.handlers.states import AuthStates
from case_workspace.telegram_bot.keyboards.main import main_menu
from case_workspace.telegram_bot.session import sessions

router = Router()


@router.message(AuthStates.waiting_password)
async def on_password(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return

    password = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    if not password:
        await message.answer("Пароль пуст. Попробуйте ещё раз.")
        return

    # Логин: фиксировано "admin" (или username Telegram, если его нет)
    login = "admin"

    try:
        result = api_client.verify(telegram_id=user.id, username=login, password=password)
    except ApiError as exc:
        if exc.status_code == 0:
            await message.answer(
                "⚠️ API недоступен. Убедитесь, что программа запущена."
            )
        elif exc.status_code == 401:
            left = exc.detail.get("attempts_left", "") if isinstance(exc.detail, dict) else ""
            await message.answer(f"❌ Неверный пароль. Осталось: {left}")
        elif exc.status_code == 423:
            until = exc.detail.get("locked_until", "") if isinstance(exc.detail, dict) else ""
            await message.answer(f"🔒 Аккаунт заблокирован до {until}")
        elif exc.status_code == 403:
            await message.answer("⛔ Доступ запрещён.")
        else:
            await message.answer(f"Ошибка: {exc.detail}")
        return

    sessions.set(user.id, result["token"])
    await state.clear()
    await message.answer(
        f"✅ Добро пожаловать, <b>{result.get('full_name') or login}</b>!\n"
        f"Роль: {result['role']}",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    token = sessions.get(user.id)
    if token:
        try:
            api_client.logout(token)
        except Exception:
            pass
    sessions.clear(user.id)
    await state.clear()
    await message.answer("👋 Вы вышли.")
