import logging
import asyncio
import random
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from core.sites.base import BaseParser
from core.proxy_manager import proxy_manager

logger = logging.getLogger(__name__)

class YandexParser(BaseParser):
    
    def _parse_proxy_for_playwright(self, proxy_str):
        """Превращает строку 'http://user:pass@ip:port' в словарь для Playwright."""
        if not proxy_str:
            return None
        try:
            parsed = urlparse(proxy_str)
            return {
                "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                "username": parsed.username,
                "password": parsed.password
            }
        except Exception:
            return None

    async def parse(self, url: str):
        # Определяем количество попыток. 
        # Если прокси есть, пробуем 3 раза. Если нет — 1 раз.
        max_retries = 4 if proxy_manager.get_proxy_count() > 1 else 1
        
        for attempt in range(max_retries):
            # Берем новый прокси для каждой попытки
            proxy_str = proxy_manager.get_proxy()
            playwright_proxy = self._parse_proxy_for_playwright(proxy_str)
            
            log_prefix = f"[Попытка {attempt+1}/{max_retries}]"
            logger.info(f"{log_prefix} YM: Запуск через прокси: {proxy_str if proxy_str else 'Свой IP'}")

            async with async_playwright() as p:
                try:
                    # Запуск браузера с прокси (или без)
                    browser = await p.chromium.launch(
                        headless=True,
                        proxy=playwright_proxy, # <-- Подключаем прокси
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        viewport={'width': 1920, 'height': 1080},
                        locale='ru-RU',
                        # Важно: передаем авторизацию прокси в контекст, если она есть
                        http_credentials={'username': playwright_proxy['username'], 'password': playwright_proxy['password']} if playwright_proxy and playwright_proxy.get('username') else None
                    )
                    
                    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    page = await context.new_page()

                    # Переходим на страницу
                    try:
                        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    except Exception as e:
                        logger.warning(f"{log_prefix} Таймаут или ошибка загрузки: {e}")
                        await browser.close()
                        continue # Пробуем следующий прокси

                    await asyncio.sleep(random.uniform(3, 6))

                    # --- Проверка на КАПЧУ ---
                    page_content = await page.content()
                    if "showcaptcha" in page.url or "captcha" in page_content.lower() or "подтвердите, что вы человек" in page_content.lower():
                        logger.warning(f"{log_prefix} YM: Обнаружена капча. Меняем IP...")
                        await browser.close()
                        continue # КАПЧА -> СЛЕДУЮЩАЯ ПОПЫТКА

                    # --- Ищем Цену ---
                    price = 0
                    try:
                        price_locator = page.locator('[data-auto="snippet-price-current"]').first
                        if await price_locator.count() > 0:
                            text = await price_locator.inner_text()
                            price = float("".join(filter(str.isdigit, text)))
                    except: pass

                    if price == 0:
                        try:
                            meta = page.locator('meta[itemprop="price"]').first
                            if await meta.count() > 0:
                                price = float(await meta.get_attribute("content"))
                        except: pass

                    # --- Ищем Название ---
                    name = "Товар Яндекс.Маркет"
                    try:
                        h1 = page.locator("h1").first
                        if await h1.count() > 0:
                            name = await h1.inner_text()
                    except: pass

                    # --- Ищем Картинку ---
                    image_url = ""
                    try:
                        img = page.locator('img[data-auto="gallery-image"]').first
                        if await img.count() > 0:
                            image_url = await img.get_attribute("src")
                        if not image_url:
                            meta_img = page.locator('meta[property="og:image"]').first
                            if await meta_img.count() > 0:
                                image_url = await meta_img.get_attribute("content")
                    except: pass

                    article = url.split("/")[-1].split("?")[0]
                    
                    await browser.close()

                    if price > 0:
                        # УРА! МЫ НАШЛИ ЦЕНУ!
                        return {
                            "shop": "Яндекс.Маркет",
                            "name": name,
                            "price": price,
                            "currency": "₽",
                            "image": image_url,
                            "article": article,
                            "url": url
                        }
                    else:
                        logger.warning(f"{log_prefix} Страница загрузилась, но цена не найдена.")
                        # Если цена 0, это может быть не капча, а отсутствие товара.
                        # Но можно попробовать еще раз на всякий случай.
                        continue

                except Exception as e:
                    logger.error(f"{log_prefix} Ошибка внутри Playwright: {e}")
                    # Закрываем и пробуем снова
                    try: await browser.close()
                    except: pass
                    continue

        # Если цикл закончился, а цену так и не вернули
        return {"error": "Не удалось получить цену даже после нескольких попыток (везде капча или ошибки)."}