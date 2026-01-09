import logging
import asyncio
import random
from playwright.async_api import async_playwright
from core.sites.base import BaseParser

logger = logging.getLogger(__name__)

class DnsParser(BaseParser):
    async def parse(self, url: str):
        async with async_playwright() as p:
            # Запускаем браузер
            # headless=False — окно будет видно (для теста)
            # Если всё ок, поменяй потом на True
            browser = await p.chromium.launch(
                headless=False, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
            )
            
            # === РУЧНАЯ МАСКИРОВКА (STEALTH) ===
            # 1. Скрываем, что мы автоматизированный софт
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 2. Подделываем плагины (у ботов их обычно нет)
            await context.add_init_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            # 3. Подделываем языки
            await context.add_init_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en'],
                });
            """)
            # ===================================
            
            page = await context.new_page()

            try:
                logger.info(f"DNS: Открываю {url}")
                
                # DNS может грузиться долго
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                
                # Имитация человека: рандомные движения
                await asyncio.sleep(random.uniform(2, 5))
                try:
                    await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    await page.mouse.wheel(0, 500) # Прокрутка вниз
                except: pass
                
                # Ждем цену
                try:
                    # Ждем чуть дольше для DNS
                    await page.wait_for_selector(".product-buy__price, .product-buy__price_active", timeout=20000)
                except:
                    logger.warning("DNS: Селектор цены не появился.")
                    await page.screenshot(path="dns_debug.png")

                price = 0
                name = "Товар DNS"
                image_url = ""

                # --- 1. ЦЕНА ---
                price_el = page.locator(".product-buy__price").first
                if await price_el.count() == 0:
                    price_el = page.locator(".product-buy__price_active").first

                if await price_el.count() > 0:
                    text = await price_el.inner_text()
                    # Чистим "143 999 ₽" -> 143999.0
                    clean_text = "".join(filter(str.isdigit, text))
                    if clean_text:
                        price = float(clean_text)

                # --- 2. НАЗВАНИЕ ---
                h1 = page.locator("h1").first
                if await h1.count() > 0:
                    name = await h1.inner_text()

                # --- 3. КАРТИНКА ---
                try:
                    img = page.locator(".product-images-slider__main-img").first
                    if await img.count() > 0:
                        image_url = await img.get_attribute("src")
                except: pass

                # Артикул
                parts = url.split("product/")
                article = parts[1].split("/")[0] if len(parts) > 1 else "dns_item"

                if price == 0:
                    return {"error": "Цена не найдена (возможно, блокировка)."}

                return {
                    "shop": "DNS",
                    "name": name,
                    "price": price,
                    "currency": "₽",
                    "image": image_url,
                    "article": article,
                    "url": url
                }

            except Exception as e:
                logger.error(f"DNS Error: {e}")
                return {"error": f"Ошибка DNS: {e}"}
            finally:
                await browser.close()