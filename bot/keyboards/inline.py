from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def item_actions_kb(item_id: int, current_page: int = 1):
    kb = [
        [
            InlineKeyboardButton(text="📉 История", callback_data=f"hist_{item_id}"),
            InlineKeyboardButton(text="✏️ Имя", callback_data=f"rename_{item_id}")
        ],
        [
            # НОВАЯ КНОПКА
            InlineKeyboardButton(text="🎯 Цель", callback_data=f"target_{item_id}"), 
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{item_id}")
        ],
        [InlineKeyboardButton(text="🔙 К списку", callback_data=f"list_page_{current_page}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def paginated_items_kb(items, total_items, page: int = 1, page_size: int = 5):
    """Клавиатура для списка с пагинацией (⬅️, 📄 1/3, ➡️)."""
    builder = InlineKeyboardBuilder()
    
    for item in items:
        name = item['name'][:25] + ".." if len(item['name']) > 25 else item['name']
        builder.button(
            text=f"{name} - {item['last_price']} ₽", 
            callback_data=f"show_item_{item['id']}_{page}"
        )
    
    builder.adjust(1) 

    total_pages = math.ceil(total_items / page_size)
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"list_page_{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"list_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    return builder.as_markup()