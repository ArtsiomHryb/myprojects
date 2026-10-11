import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Optional, Union

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand, BotCommandScopeDefault,
    ReplyKeyboardRemove, Update
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ------------------------- Настройки -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8632216406:AAHafYGI3CcJkE9TvPfSnXGI2rJWRyhLXbM")
DB_PATH = os.getenv("DB_PATH", "people.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------- База данных -------------------------
class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    full_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def add_person(self, user_id: int, full_name: str, birth_date: str, phone: str) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO people (user_id, full_name, birth_date, phone, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, full_name, birth_date, phone, datetime.now().isoformat())
            )
            await db.commit()
            return cursor.lastrowid

    async def get_by_user(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT id, full_name, birth_date, phone FROM people WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def get_by_id(self, record_id: int):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT id, user_id, full_name, birth_date, phone FROM people WHERE id = ?",
                (record_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def delete(self, record_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "DELETE FROM people WHERE id = ? AND user_id = ?",
                (record_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM people WHERE user_id = ?", (user_id,)) as cursor:
                return (await cursor.fetchone())[0]

db = Database(DB_PATH)

# ------------------------- FSM -------------------------
class AddForm(StatesGroup):
    full_name = State()
    birth_date = State()
    phone = State()

# ------------------------- Клавиатуры -------------------------
def main_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Добавить запись")
    builder.button(text="📋 Мои записи")
    builder.button(text="❌ Отмена")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)

def records_kb(records) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rec in records:
        builder.button(text=f"🗑 Удалить #{rec[0]}", callback_data=f"del:{rec[0]}")
    builder.adjust(1)
    return builder.as_markup()

# ------------------------- Валидация -------------------------
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
PHONE_RE = re.compile(r"^\+?\d{10,15}$")
NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z\-\s]{3,100}$")

def validate_name(value: str) -> Optional[str]:
    value = value.strip()
    if not NAME_RE.match(value):
        return None
    return " ".join(value.split()).title()

def validate_date(value: str) -> Optional[str]:
    value = value.strip()
    if not DATE_RE.match(value):
        return None
    try:
        d = datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return None
    if d > datetime.now() or d.year < 1900:
        return None
    return value

def validate_phone(value: str) -> Optional[str]:
    value = re.sub(r"[\s\-\(\)]", "", value.strip())
    if not PHONE_RE.match(value):
        return None
    return value

# ------------------------- Роутер -------------------------
router = Router()

# ------------------------- Команды -------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    count = await db.count(message.from_user.id)
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        f"Я бот для хранения анкет.\n"
        f"У вас сохранено записей: <b>{count}</b>\n\n"
        f"Нажмите «➕ Добавить запись», чтобы ввести ФИО, дату рождения и номер.",
        reply_markup=main_kb()
    )

@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Нечего отменять.", reply_markup=main_kb())
        return
    await state.clear()
    await message.answer("❌ Ввод отменён.", reply_markup=main_kb())

# ------------------------- Добавление -------------------------
@router.message(F.text == "➕ Добавить запись")
@router.message(Command("add"))
async def add_start(message: Message, state: FSMContext):
    await state.set_state(AddForm.full_name)
    await message.answer(
        "Шаг 1/3. Введите <b>ФИО</b> человека.\n"
        "Пример: <code>Иванов Иван Иванович</code>",
        reply_markup=cancel_kb()
    )

@router.message(AddForm.full_name)
async def add_name(message: Message, state: FSMContext):
    name = validate_name(message.text or "")
    if not name:
        await message.answer("⚠️ Некорректное ФИО. Введите буквами, минимум 3 символа.\nПример: <code>Иванов Иван Иванович</code>")
        return
    await state.update_data(full_name=name)
    await state.set_state(AddForm.birth_date)
    await message.answer(
        "Шаг 2/3. Введите <b>дату рождения</b> в формате <code>ДД.ММ.ГГГГ</code>.\n"
        "Пример: <code>15.03.1990</code>",
        reply_markup=cancel_kb()
    )

@router.message(AddForm.birth_date)
async def add_date(message: Message, state: FSMContext):
    date = validate_date(message.text or "")
    if not date:
        await message.answer("⚠️ Некорректная дата. Формат: <code>ДД.ММ.ГГГГ</code>, дата не в будущем.\nПример: <code>15.03.1990</code>")
        return
    await state.update_data(birth_date=date)
    await state.set_state(AddForm.phone)
    await message.answer(
        "Шаг 3/3. Введите <b>абонентский номер</b>.\n"
        "Пример: <code>+375291234567</code> или <code>375291234567</code>",
        reply_markup=cancel_kb()
    )

@router.message(AddForm.phone)
async def add_phone(message: Message, state: FSMContext):
    phone = validate_phone(message.text or "")
    if not phone:
        await message.answer("⚠️ Некорректный номер. Только цифры (10–15), можно с «+».\nПример: <code>+375291234567</code>")
        return

    data = await state.get_data()
    record_id = await db.add_person(
        message.from_user.id,
        data["full_name"],
        data["birth_date"],
        phone
    )
    await state.clear()

    await message.answer(
        f"✅ Запись сохранена!\n\n"
        f"🆔 <b>#{record_id}</b>\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"🎂 Дата рождения: {data['birth_date']}\n"
        f"📞 Телефон: {phone}",
        reply_markup=main_kb()
    )

# ------------------------- Список записей -------------------------
@router.message(F.text == "📋 Мои записи")
@router.message(Command("list"))
async def list_records(message: Message):
    records = await db.get_by_user(message.from_user.id)
    if not records:
        await message.answer("📭 У вас пока нет записей. Нажмите «➕ Добавить запись».")
        return

    lines = ["📋 <b>Ваши записи:</b>\n"]
    for rec in records:
        rid, full_name, birth_date, phone = rec
        lines.append(
            f"🆔 <b>#{rid}</b>\n"
            f"👤 {full_name}\n"
            f"🎂 {birth_date}\n"
            f"📞 {phone}\n"
        )
    await message.answer(
        "\n".join(lines),
        reply_markup=records_kb(records)
    )

# ------------------------- Удаление -------------------------
@router.callback_query(F.data.startswith("del:"))
async def delete_record(callback: CallbackQuery):
    record_id = int(callback.data.split(":")[1])
    record = await db.get_by_id(record_id)
    if not record:
        await callback.answer("Запись уже удалена.", show_alert=True)
        return
    if record[1] != callback.from_user.id:
        await callback.answer("Это не ваша запись.", show_alert=True)
        return

    ok = await db.delete(record_id, callback.from_user.id)
    if ok:
        await callback.answer(f"Запись #{record_id} удалена.")
        await callback.message.edit_text(
            f"🗑 Запись <b>#{record_id}</b> удалена.",
            reply_markup=None
        )
    else:
        await callback.answer("Не удалось удалить.", show_alert=True)

# ------------------------- Фолбэк -------------------------
@router.message()
async def fallback(message: Message):
    await message.answer(
        "🤔 Не понял. Используйте кнопки меню.",
        reply_markup=main_kb()
    )

# ------------------------- Запуск -------------------------
async def on_startup(bot: Bot):
    await db.init()
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="add", description="Добавить запись"),
        BotCommand(command="list", description="Мои записи"),
        BotCommand(command="cancel", description="Отменить ввод"),
    ], scope=BotCommandScopeDefault())

async def main():
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("Укажите BOT_TOKEN! Пример: export BOT_TOKEN='123:ABC...'")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    @dp.errors()
    async def errors_handler(update: Update, exception: Exception):
        logger.exception(f"Ошибка при обработке {update}: {exception}")
        return True

    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())