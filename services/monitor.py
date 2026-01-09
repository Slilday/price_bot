import asyncio
import random
from bot.keyboards.inline import item_actions_kb
from database.db import db
from core.parser_manager import ParserManager

parser_manager = ParserManager()

async def run_price_monitor(bot):
    print("🕵️‍♂️ Плавный мониторинг цен запущен!")
    
    while True:
        items = await db.get_all_items()
        
        if not items:
            await asyncio.sleep(600)
            continue

        print(f"🔄 Новый цикл проверки для {len(items)} товаров...")

        CHECK_WINDOW_SECONDS = 2 * 3600
        num_items = len(items)
        average_sleep_per_item = CHECK_WINDOW_SECONDS / num_items if num_items > 0 else CHECK_WINDOW_SECONDS

        for item in items:
            try:
                # --- ЛОГИКА ПРОВЕРКИ ---
                result = await parser_manager.get_price(item['url'])
                
                if "error" in result:
                    print(f"⚠️ {item['url']}: {result['error']}")
                    continue

                new_price = result['price']
                old_price = item['last_price']
                
                if new_price <= 0 or old_price <= 0: continue
                
                # ВЫСЧИТЫВАЕМ ИЗМЕНЕНИЕ В %
                change_percent = abs((new_price - old_price) / old_price) * 100
                
                # ПОЛУЧАЕМ ПОРОГ ПОЛЬЗОВАТЕЛЯ
                user_threshold = await db.get_user_threshold(item['user_id'])
                
                # СРАВНИВАЕМ
                if change_percent >= user_threshold:
                    await db.update_item_price(item['id'], new_price)
                    
                    user_id = item['user_id']
                    diff = new_price - old_price
                    
                    if diff < 0:
                        msg = f"📉 Цена снизилась на {change_percent:.1f}%!"
                    else:
                        msg = f"📈 Цена выросла на {change_percent:.1f}%!"
                        
                    text = (f"{msg}\n\n"
                            f"📦 {item['name']}\n"
                            f"Было: {old_price} ₽\n"
                            f"Стало: **{new_price} ₽**")
                    
                    try:
                        await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=item_actions_kb(item['id']))
                        print(f"🔔 Уведомление для {user_id} (порог {user_threshold}%, изменение {change_percent:.1f}%)")
                    except Exception as e:
                        print(f"❌ Не удалось отправить: {e}")

            except Exception as e:
                print(f"❌ Критическая ошибка монитора: {e}")
            
            # --- СОН ---
            min_sleep = average_sleep_per_item * 0.8
            max_sleep = average_sleep_per_item * 1.2
            await asyncio.sleep(int(random.uniform(min_sleep, max_sleep)))