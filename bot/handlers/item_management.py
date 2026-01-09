from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from bot.states import BotStates
from bot.keyboards.reply import cancel_kb, main_menu_kb
from bot.keyboards.inline import item_actions_kb, paginated_items_kb # <--- Проверь этот импорт!
from core.parser_manager import ParserManager
from database.db import db
from services.plotter import create_price_plot

router = Router()
parser_manager = ParserManager()
# --- Вспомогательная функция для списка (оставляем) ---
def format_items_text(items_list):
    # ... (код этой функции не меняется)
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
            text_lines.append(f"\n{emoji} **{current_shop}**")
        name = item['name'][:25] + ".." if len(item['name']) > 25 else item['name']
        price = f"{item['last_price']} ₽"
        text_lines.append(f"**{index}.** {name} — `{price}`")
    text_lines.append("\n👇 *Нажмите номер для управления:*")
    return "\n".join(text_lines), items_list


# --- ДОБАВЛЕНИЕ ТОВАРА ---
@router.message(F.text == "➕ Добавить товар")
@router.message(Command("add"))
async def start_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔗 Пришлите ссылку на товар:", reply_markup=cancel_kb())
    await state.set_state(BotStates.waiting_for_link_to_add)

@router.message(BotStates.waiting_for_link_to_add)
async def process_add_link(message: types.Message, state: FSMContext):
    # === НОВАЯ ПРОВЕРКА ОТМЕНЫ ===
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())
        return
    # ==========================
    
    link = message.text.strip()
    status_msg = await message.answer("🔎 Ищу товар...")
    result = await parser_manager.get_price(link)
    await state.clear()

    if "error" in result:
        await status_msg.delete()
        await message.answer(f"❌ Ошибка: {result['error']}", reply_markup=main_menu_kb())
    else:
        # ... (код сохранения и отправки карточки не меняется)
        item_id = None
        try:
            await db.add_user(message.from_user.id, message.from_user.username or "User")
            item_id = await db.add_item(
                user_id=message.from_user.id,
                url=result['url'],
                shop=result['shop'],
                name=result['name'],
                article=str(result.get('article', '')),
                price=result['price'],
                image=result.get('image', '')
            )
        except Exception as e:
            print(f"Ошибка БД: {e}")

        text = (f"✅ **{result['name']}**\n💰 {result['price']} {result['currency']}")
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

# --- ОСТАЛЬНЫЕ ФУНКЦИИ С ТАКОЙ ЖЕ ПРОВЕРКОЙ ---
@router.message(F.text == "🗑 Удалить товар")
@router.message(Command("delete"))
async def start_delete(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🗑 Пришлите ссылку для удаления:", reply_markup=cancel_kb())
    await state.set_state(BotStates.waiting_for_link_to_delete)

@router.message(BotStates.waiting_for_link_to_delete)
async def process_delete_link(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb())
        return
        
    await db.delete_item(message.from_user.id, message.text.strip())
    await message.answer("❌ Товар удален.", reply_markup=main_menu_kb())
    await state.clear()


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
        await message.answer("❌ Нет данных.", reply_markup=main_menu_kb())
        return

    user_theme = await db.get_user_theme(message.from_user.id)
    plot_buffer = create_price_plot(history, theme=user_theme)
    if plot_buffer:
        photo = BufferedInputFile(plot_buffer.read(), filename="chart.png")
        await message.answer_photo(photo, caption="📉 История цен", reply_markup=main_menu_kb())
    else:
        await message.answer("Ошибка графика.", reply_markup=main_menu_kb())
    await state.clear()


@router.message(F.text == "📋 Мои товары")
@router.message(Command("list"))
async def show_my_items(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    page = 1
    page_size = 5

    items, total_items = await db.get_user_items_paginated(user_id, page, page_size)
    
    if not items:
        await message.answer("🤷‍♂️ Ваш список пуст.", reply_markup=main_menu_kb())
        return

    keyboard = paginated_items_kb(items, total_items, page, page_size)
    
    await message.answer(
        f"📋 **Ваши товары (Страница {page}):**", 
        reply_markup=keyboard
    )

@router.message(BotStates.waiting_for_new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    # Если нажали "Назад", выходим
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("✅ Переименование отменено.", reply_markup=main_menu_kb())
        return
        
    # Достаем ID товара из "памяти" состояния
    data = await state.get_data()
    item_id = data.get("item_id_to_rename")
    
    if not item_id:
        await state.clear()
        await message.answer("❌ Произошла ошибка. Попробуйте снова.", reply_markup=main_menu_kb())
        return

    new_name = message.text.strip()
    
    # Обновляем в базе
    await db.rename_item(item_id, new_name)
    
    # Выходим из состояния
    await state.clear()
    
    await message.answer(f"✅ Готово! Товар переименован в «**{new_name}**».", parse_mode="Markdown", reply_markup=main_menu_kb())