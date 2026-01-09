import asyncio
import random
import logging
import time
from bot.keyboards.inline import item_actions_kb
from database.db import db
from core.parser_manager import ParserManager
from core.proxy_manager import proxy_manager

logger = logging.getLogger(__name__)
parser_manager = ParserManager()

# Список "тяжелых" магазинов (5 часов)
HEAVY_SHOPS = ["wildberries.ru", "market.yandex.ru", "dns-shop.ru", "ozon.ru"]

async def run_price_monitor(bot):
    logger.info("🕵️‍♂️ Умный мониторинг запущен (Интервальный)!")
    
    while True:
        try:
            items = await db.get_all_items()
            
            # Если товаров нет, спим минуту и проверяем снова
            if not items:
                await asyncio.sleep(60)
                continue

            # Считаем, сколько у нас живых прокси
            proxies_count = proxy_manager.get_proxy_count()
            
            # Флаг, делали ли мы хоть одну проверку в этом цикле
            checked_something = False

            for item in items:
                current_time = time.time()
                last_check = item['last_check'] if item['last_check'] else 0
                
                # 1. Определяем интервал проверки
                is_heavy = any(shop in item['url'] for shop in HEAVY_SHOPS)
                
                if is_heavy:
                    check_interval = 5 * 3600  # 5 часов для WB/Яндекс
                else:
                    check_interval = 1 * 3600  # 1 час для Steam/Ситилинк

                # 2. Если время еще не пришло — пропускаем товар
                if current_time - last_check < check_interval:
                    continue
                
                # Если дошли сюда, значит пора проверять!
                checked_something = True
                
                try:
                    # --- ПРОВЕРКА ЦЕНЫ ---
                    result = await parser_manager.get_price(item['url'])
                    
                    if "error" in result:
                        logger.warning(f"⚠️ {item['url']}: {result['error']}")
                        # Обновляем время даже при ошибке, чтобы не долбить товар каждую секунду
                        await db.update_last_check(item['id'])
                    else:
                        new_price = result['price']
                        old_price = item['last_price']
                        
                        # Если цена валидная
                        if new_price > 0:
                            # Обновляем в любом случае (чтобы обновить last_check)
                            await db.update_item_price(item['id'], new_price)
                            
                            # Если цена изменилась по сравнению с прошлой
                            if new_price != old_price and old_price > 0:
                                user_id = item['user_id']
                                target_price = item['target_price']
                                should_notify = False
                                notification_text = ""

                                # Проверка Целевой цены
                                if target_price > 0:
                                    if new_price <= target_price and old_price > target_price:
                                        should_notify = True
                                        notification_text = f"🎯 **ЦЕЛЬ ДОСТИГНУТА!**\n\n📦 {item['name']}\nЦена: **{new_price} ₽**"
                                # Проверка процента
                                else:
                                    change_percent = abs((new_price - old_price) / old_price) * 100
                                    user_threshold = await db.get_user_threshold(user_id)
                                    if change_percent >= user_threshold:
                                        should_notify = True
                                        emoji = "📉" if new_price < old_price else "📈"
                                        notification_text = f"{emoji} Цена изменилась ({change_percent:.1f}%)\n\n📦 {item['name']}\n{old_price} -> **{new_price} ₽**"

                                if should_notify:
                                    try:
                                        await bot.send_message(chat_id=user_id, text=notification_text, parse_mode="Markdown", reply_markup=item_actions_kb(item['id']))
                                        logger.info(f"🔔 Уведомление для {user_id}")
                                    except Exception as e:
                                        logger.error(f"Не удалось отправить: {e}")

                except Exception as e:
                    logger.error(f"Ошибка проверки товара {item['id']}: {e}")

                # 3. ПАУЗА ПОСЛЕ ПРОВЕРКИ (Anti-Ban)
                if is_heavy:

                    sleep_time = random.uniform(70, 100) / proxies_count
                else:

                    sleep_time = random.uniform(8, 15)
                
                logger.info(f"💤 Сплю {sleep_time:.1f} сек...")
                await asyncio.sleep(sleep_time)

            # Если мы пробежались по списку и ничего не проверяли (все свежие),
            # спим 30 секунд, чтобы не грузить процессор пустым циклом
            if not checked_something:
                await asyncio.sleep(30)

        except Exception as e:
            logger.critical(f"❌ Критическая ошибка монитора: {e}")
            await asyncio.sleep(60)