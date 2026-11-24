"""/start и /help."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from case_workspace.telegram_bot.handlers.states import AuthStates
from case_workspace.telegram_bot.keyboards.main import main_menu
from case_workspace.telegram_bot.session import sessions

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return
    if sessions.get(user.id):
        await message.answer("👋 С возвращением!", reply_markup=main_menu())
        return
    await state.set_state(AuthStates.waiting_password)
    await message.answer(
        "🔐 <b>Case Workspace</b>\n\n"
        "Введите пароль от учётной записи в программе.\n\n"
        "⚠️ Сообщение с паролем будет удалено из чата.",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Справка</b>\n\n"
        "/start — войти\n"
        "/cases — список дел\n"
        "/deadlines — ближайшие сроки\n"
        "/logout — выйти\n"
        "/help — эта справка\n\n"
        "Отправьте идентификатор (карту, IBAN, телефон, IP) — "
        "бот определит его.",
        parse_mode="HTML",
    )
