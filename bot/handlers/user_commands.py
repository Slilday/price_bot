from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot.keyboards.reply import main_menu_kb
from database.db import db
from aiogram.filters import CommandObject

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await db.add_user(message.from_user.id, message.from_user.username or "User")
    
    text = (
        "👋 **Привет! Я Price Monitor Bot.**\n\n"
        "Я помогаю экономить, отслеживая цены на товары. Просто отправь мне ссылку, и я уведомлю тебя, когда цена снизится!\n\n"
        "🛒 **Поддерживаемые магазины:**\n"
        "⚫ **Steam** (Игры)\n"
        "🟠 **Ситилинк**\n\n"
        "👇 **Нажмите «➕ Добавить товар» в меню ниже, чтобы начать!**"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.message(F.text == "ℹ️ Инфо")
@router.message(Command("info"))
async def cmd_info(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "ℹ️ **Справка по командам**\n\n"
        "**Управление товарами:**\n"
        "/add — ➕ Добавить товар\n"
        "/list — 📋 Мои товары\n"
        "/delete — 🗑 Удалить товар\n"
        "/history — 📉 История цен\n\n"
        "**Настройки графиков:**\n"
        "/black — 🌑 Темная тема\n"
        "/white — ☀️ Светлая тема\n\n"
        "**Общее:**\n"
        "/start — 🔄 Перезапуск\n"
        "/info — ℹ️ Эта справка\n"
        "/threshold - Установить порог уведомления об изменении цены"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.message(Command("black"))
async def cmd_black(message: types.Message):
    await db.add_user(message.from_user.id, message.from_user.username or "User")
    await db.set_user_theme(message.from_user.id, "dark")
    await message.answer("🌑 **Темная тема** для графиков включена!", parse_mode="Markdown")

@router.message(Command("white"))
async def cmd_white(message: types.Message):
    await db.add_user(message.from_user.id, message.from_user.username or "User")
    await db.set_user_theme(message.from_user.id, "light")
    await message.answer("☀️ **Светлая тема** для графиков включена!", parse_mode="Markdown")

@router.message(F.text == "🔙 Назад")
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_kb())



@router.message(Command("threshold"))
async def cmd_threshold(message: types.Message, command: CommandObject):
    
    user_id = message.from_user.id

    if not command.args:
        current_threshold = await db.get_user_threshold(user_id)
        await message.answer(
            f"📈 Ваш текущий порог: **{current_threshold}%**.\n\n"
            "Чтобы изменить, напишите, например:\n"
            "`/threshold 10` (изменение на 10%)\n"
            "`/threshold 0` (любое изменение)"
        )
        return

    try:
        new_threshold = float(command.args.replace(',', '.'))
        if not (0 <= new_threshold <= 100):
            raise ValueError

        await db.set_user_threshold(user_id, new_threshold)
        await message.answer(f"✅ Готово! Порог уведомлений изменен на **{new_threshold}%**.")

    except (ValueError, TypeError):
        await message.answer("❌ **Ошибка!** Укажите число от 0 до 100. Например: `/threshold 5`")