from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from bot.states import BotStates
from bot.keyboards.reply import cancel_kb, main_menu_kb
from bot.keyboards.inline import item_actions_kb, paginated_items_kb
from core.parser_manager import ParserManager
from database.db import db
from services.plotter import create_price_plot

router = Router()
parser_manager = ParserManager()

# --- Вспомогательная функция ---
def format_items_text(items_list):
    items_list.sort(key=lambda x: (x['shop'], x['name']))
    text_lines = ["📋 **Ваши товары:**"]
    current_shop = None
    for index, item in enumerate(items_list, start=1):
        if item['shop'] != current_shop:
            current_shop = item['shop']
            emoji = "🛒"
            if "Wildberries" in current_shop: emoji = "🟣"
            elif "Steam" in current_shop: emoji = "🎮"
            elif "Ситилинк" in current_shop: emoji = "🟠"
            elif "Яндекс.Маркет" in current_shop: emoji = "🟡"
            elif "DNS" in current_shop: emoji = "👽"
            text_lines.append(f"\n{emoji} **{current_shop}**")
        name = item['name'][:25] + ".." if len(item['name']) > 25 else item['name']
        price = f"{item['last_price']} ₽"
        text_lines.append(f"**{index}.** {name} — `{price}`")
    text_lines.append("\n👇 *Нажмите номер для управления:*")
    return "\n".join(text_lines), items_list

# --- ДОБАВЛЕНИЕ ---
@router.message(F.text == "➕ Добавить товар")
@router.message(Command("add"))
async def start_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔗 Пришлите ссылку на товар:", reply_markup=cancel_kb())
    await state.set_state(BotStates.waiting_for_link_to_add)

@router.message(BotStates.waiting_for_link_to_add)
async def process_add_link(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())
        return
    
    link = message.text.strip()
    status_msg = await message.answer("🔎 Ищу товар...")
    result = await parser_manager.get_price(link)
    await state.clear()

    if "error" in result:
        await status_msg.delete()
        await message.answer(f"❌ Ошибка: {result['error']}", reply_markup=main_menu_kb())
    else:
        # Добавляем юзера на всякий случай
        await db.add_user(message.from_user.id, message.from_user.username or "User")
        
        item_id = await db.add_item(
            user_id=message.from_user.id, url=result['url'], shop=result['shop'],
            name=result['name'], article=str(result.get('article', '')),
            price=result['price'], image=result.get('image', '')
        )
        text = f"✅ **{result['name']}**\n💰 {result['price']} {result['currency']}"
        await status_msg.delete()
        
        keyboard = item_actions_kb(item_id) if item_id else None
        
        if result.get('image'):
            try:
                await message.answer_photo(result['image'], caption=text, parse_mode="Markdown", reply_markup=keyboard)
            except:
                await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
        await message.answer("Что делаем дальше?", reply_markup=main_menu_kb())

# --- СПИСОК ---
@router.message(F.text == "📋 Мои товары")
@router.message(Command("list"))
async def show_my_items(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    page_size = 5
    items, total_items = await db.get_user_items_paginated(user_id, 1, page_size)
    if not items:
        await message.answer("🤷‍♂️ Ваш список пуст.", reply_markup=main_menu_kb())
        return
    items_list = [dict(item) for item in items]
    final_text, sorted_items = format_items_text(items_list)
    keyboard = paginated_items_kb(sorted_items, total_items, 1, page_size)
    await message.answer(f"📋 **Ваши товары (Страница 1):**", reply_markup=keyboard)

# --- УДАЛЕНИЕ ---
@router.message(F.text == "🗑 Удалить товар")
@router.message(Command("delete"))
async def start_delete(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🗑 Пришлите ссылку на товар для удаления:", reply_markup=cancel_kb())
    await state.set_state(BotStates.waiting_for_link_to_delete)

@router.message(BotStates.waiting_for_link_to_delete)
async def process_delete_link(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())
        return
    await db.delete_item(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer("✅ Товар удален (если он был в вашем списке).", reply_markup=main_menu_kb())

# --- ИСТОРИЯ ---
@router.message(F.text == "📉 История цен")
@router.message(Command("history"))
async def start_history(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📊 Пришлите ссылку на товар:", reply_markup=cancel_kb())
    await state.set_state(BotStates.waiting_for_link_history)

@router.message(BotStates.waiting_for_link_history)
async def process_history_link(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())
        return
        
    link = message.text.strip()
    history = await db.get_price_history(link)
    if not history:
        await message.answer("❌ Нет данных. Сначала добавьте товар.", reply_markup=main_menu_kb())
        await state.clear()
        return
    user_theme = await db.get_user_theme(message.from_user.id)
    plot_buffer = create_price_plot(history, theme=user_theme)
    if plot_buffer:
        photo = BufferedInputFile(plot_buffer.read(), filename="chart.png")
        await message.answer_photo(photo, caption="📉 История цен", reply_markup=main_menu_kb())
    else:
        await message.answer("Ошибка графика.", reply_markup=main_menu_kb())
    await state.clear()
    
# --- ПЕРЕИМЕНОВАНИЕ ---
@router.message(BotStates.waiting_for_new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("✅ Переименование отменено.", reply_markup=main_menu_kb())
        return
        
    data = await state.get_data()
    item_id = data.get("item_id_to_rename")
    if not item_id:
        await state.clear()
        await message.answer("❌ Ошибка контекста. Попробуйте снова.", reply_markup=main_menu_kb())
        return
    new_name = message.text.strip()
    await db.rename_item(item_id, new_name)
    await state.clear()
    await message.answer(f"✅ Готово! Товар переименован в «**{new_name}**».", parse_mode="Markdown", reply_markup=main_menu_kb())

# --- !!! НОВЫЙ ОБРАБОТЧИК: ЦЕЛЕВАЯ ЦЕНА !!! ---
@router.message(BotStates.waiting_for_target_price)
async def process_target_price(message: types.Message, state: FSMContext):
    # 1. Проверка отмены
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Настройка цели отменена.", reply_markup=main_menu_kb())
        return

    try:
        # 2. Обработка числа
        text_price = message.text.replace(' ', '').replace(',', '.')
        target = float(text_price)
        
        if target < 0: raise ValueError
        
        # 3. Получаем ID товара из памяти
        data = await state.get_data()
        item_id = data.get("item_id_for_target")
        
        if not item_id:
            await state.clear()
            await message.answer("⚠️ Ошибка: потерян ID товара. Попробуйте снова через меню.", reply_markup=main_menu_kb())
            return
        
        # 4. Сохраняем в базу (с отловом ошибок!)
        try:
            success = await db.set_target_price(item_id, target)
            if not success:
                await message.answer("❌ Ошибка: Товар не найден в базе (возможно, удален).", reply_markup=main_menu_kb())
                await state.clear()
                return
        except Exception as e:
            # Вот тут мы поймаем ошибку, если метода нет в db.py
            await message.answer(f"❌ Ошибка базы данных: {e}", reply_markup=main_menu_kb())
            await state.clear()
            return

        # 5. Успех
        await state.clear()
        
        if target > 0:
            msg = f"✅ Целевая цена установлена: **{target} ₽**.\nКак только цена упадет до этого уровня, я пришлю уведомление!"
        else:
            msg = "✅ Целевая цена сброшена."
            
        await message.answer(msg, reply_markup=main_menu_kb(), parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число (например: `15000`).")
    except Exception as e:
        # Глобальный перехватчик ошибок
        await message.answer(f"🔥 Произошла непредвиденная ошибка: {e}", reply_markup=main_menu_kb())
        await state.clear()