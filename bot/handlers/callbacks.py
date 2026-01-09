from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database.db import db
from services.plotter import create_price_plot
from aiogram.types import BufferedInputFile
from bot.keyboards.inline import item_actions_kb, paginated_items_kb
from bot.states import BotStates
from bot.keyboards.reply import cancel_kb

router = Router()

# --- Вспомогательная функция для отображения страницы списка ---
async def show_list_page(callback: types.CallbackQuery, page: int = 1):
    user_id = callback.from_user.id
    page_size = 5
    items, total_items = await db.get_user_items_paginated(user_id, page, page_size)

    if not items:
        try:
            await callback.message.edit_text("🤷‍♂️ Ваш список теперь пуст.")
        except:
            await callback.message.answer("🤷‍♂️ Ваш список теперь пуст.")
        return

    keyboard = paginated_items_kb(items, total_items, page, page_size)
    
    try:
        await callback.message.edit_text(
            f"📋 **Ваши товары (Страница {page}):**",
            reply_markup=keyboard
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"📋 **Ваши товары (Страница {page}):**",
            reply_markup=keyboard
        )

# ==========================================
# ОБРАБОТЧИКИ КНОПОК
# ==========================================

# 1. ПЕРЕЛИСТЫВАНИЕ СТРАНИЦ
@router.callback_query(F.data.startswith("list_page_"))
async def callback_list_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_list_page(callback, page)
    await callback.answer()

# 2. ПОКАЗ КАРТОЧКИ ТОВАРА (При нажатии на название в списке)
@router.callback_query(F.data.startswith("show_item_"))
async def callback_show_item(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    item_id = int(parts[2])
    page = int(parts[3])
    
    item = await db.get_item_by_id(item_id)
    if not item:
        await callback.answer("Товар не найден (возможно, удален)", show_alert=True)
        return

    # Безопасное получение целевой цены (чтобы не было ошибки IndexError)
    try:
        target_price = item['target_price']
    except (IndexError, KeyError):
        target_price = 0

    target_text = f"**{target_price} ₽**" if target_price > 0 else "не задана"

    text = (f"🛒 **{item['shop']}**\n"
            f"📦 **{item['name']}**\n"
            f"💰 Цена: **{item['last_price']} ₽**\n"
            f"🎯 Цель: {target_text}\n"
            f"🔗 [Ссылка на товар]({item['url']})")

    keyboard = item_actions_kb(item_id, current_page=page)
    
    # Удаляем список и присылаем карточку (так надежнее для картинок)
    await callback.message.delete()
    if item['image_url']:
        try:
            await callback.message.answer_photo(photo=item['image_url'], caption=text, parse_mode="Markdown", reply_markup=keyboard)
        except:
            await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

# 3. УДАЛЕНИЕ ТОВАРА
@router.callback_query(F.data.startswith("del_"))
async def callback_delete(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    item = await db.get_item_by_id(item_id)
    
    if item:
        await db.delete_item(callback.from_user.id, item['url'])
        await callback.answer("✅ Товар удален!", show_alert=True)
        # Возвращаемся на 1-ю страницу списка
        await show_list_page(callback, page=1)
    else:
        await callback.answer("❌ Товар уже был удален", show_alert=True)

# 4. ИСТОРИЯ ЦЕН (ГРАФИК)
@router.callback_query(F.data.startswith("hist_"))
async def callback_history(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    item = await db.get_item_by_id(item_id)
    
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
        
    history = await db.get_price_history(item['url'])
    user_theme = await db.get_user_theme(callback.from_user.id)
    
    await callback.answer("🎨 Рисую график...")
    
    plot_buffer = create_price_plot(history, theme=user_theme)
    
    if plot_buffer:
        photo = BufferedInputFile(plot_buffer.read(), filename="chart.png")
        await callback.message.answer_photo(photo, caption=f"📉 График для: {item['name']}")
    else:
        await callback.message.answer("Недостаточно данных для графика.")

# 5. ПЕРЕИМЕНОВАНИЕ
@router.callback_query(F.data.startswith("rename_"))
async def callback_start_rename(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[1])
    # Запоминаем ID и переводим бота в режим ожидания текста
    await state.update_data(item_id_to_rename=item_id)
    await state.set_state(BotStates.waiting_for_new_name)
    
    await callback.answer()
    await callback.message.answer("✏️ Введите новое название для товара:", reply_markup=cancel_kb())

# 6. ЦЕЛЕВАЯ ЦЕНА (TARGET PRICE)
@router.callback_query(F.data.startswith("target_"))
async def callback_set_target(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[1])
    item = await db.get_item_by_id(item_id)
    
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Запоминаем ID и переводим бота в режим ожидания цены
    await state.update_data(item_id_for_target=item_id)
    await state.set_state(BotStates.waiting_for_target_price)
    
    try:
        current_target = item['target_price']
    except:
        current_target = 0
        
    text_current = f"(Сейчас: {current_target} ₽)" if current_target > 0 else "(Сейчас: не задана)"
    
    await callback.answer()
    await callback.message.answer(
        f"🎯 **Настройка целевой цены**\n"
        f"Товар: {item['name']}\n"
        f"Текущая цена: {item['last_price']} ₽\n"
        f"{text_current}\n\n"
        "Введите цену, ниже которой вы хотите получить уведомление (просто число).\n"
        "Отправьте `0`, чтобы удалить цель.",
        reply_markup=cancel_kb(),
        parse_mode="Markdown"
    )

# 7. ПУСТАЯ КНОПКА (Номер страницы)
@router.callback_query(F.data == "noop")
async def callback_noop(callback: types.CallbackQuery):
    await callback.answer()