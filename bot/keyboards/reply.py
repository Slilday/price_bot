from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb():
    kb = [
        [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="📋 Мои товары")],
        [KeyboardButton(text="📉 История цен"), KeyboardButton(text="ℹ️ Инфо")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True, 
        input_field_placeholder="Выберите действие"
    )

def cancel_kb():
    kb = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True, 
        input_field_placeholder="Нажмите Назад для отмены"
    )