import re
import json
from bs4 import BeautifulSoup
from core.sites.base import BaseParser

class CitilinkParser(BaseParser):
    def _get_id(self, url: str):
        match = re.search(r"product/.*?(\d+)/?", url)
        if match:
            return match.group(1)
        return None

    async def parse(self, url: str):
        product_id = self._get_id(url)
        if not product_id:
            return {"error": "Не удалось найти ID товара."}

        # Скачиваем HTML
        html = await self.make_request(url, json=False)
        
        if not html:
            return {"error": "Ситилинк не открывается (возможно, блокировка)."}

        soup = BeautifulSoup(html, "html.parser")

        name = "Товар Ситилинк"
        price = 0
        image_url = ""

        # 1. Пробуем найти JSON-LD
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                if not script.string: continue
                data = json.loads(script.string)
                
                # Ищем структуру Product
                if data.get("@type") == "Product":
                    name = data.get("name", name)
                    
                    # === ИСПРАВЛЕНИЕ КАРТИНКИ ===
                    raw_img = data.get("image")
                    if raw_img:
                        if isinstance(raw_img, str):
                            # Если это просто строка
                            image_url = raw_img
                        elif isinstance(raw_img, list) and len(raw_img) > 0:
                            # Если это список (наш случай)
                            first_img = raw_img[0]
                            if isinstance(first_img, str):
                                image_url = first_img
                            elif isinstance(first_img, dict):
                                image_url = first_img.get('url') or first_img.get('contentUrl')
                        elif isinstance(raw_img, dict):
                            # Если это словарь
                            image_url = raw_img.get('url') or raw_img.get('contentUrl')
                    # ============================
                    
                    offers = data.get("offers", {})
                    if isinstance(offers, dict):
                        price = float(offers.get("price", 0))
                    elif isinstance(offers, list) and offers:
                        price = float(offers[0].get("price", 0))
                    
                    if price > 0:
                        break
            except:
                continue

        # 2. Если JSON не сработал или там не было цены
        if price == 0:
            price_meta = soup.find("meta", {"itemprop": "price"})
            if price_meta:
                try:
                    price = float(price_meta.get("content"))
                except: pass

        # 3. Дополнительные проверки названия и картинки
        if name == "Товар Ситилинк":
            h1 = soup.find("h1")
            if h1: name = h1.get_text(strip=True)

        # Если картинка не нашлась в JSON, ищем в мета-тегах
        if not image_url or not isinstance(image_url, str):
            img_meta = soup.find("meta", {"property": "og:image"})
            if img_meta: 
                image_url = img_meta.get("content")

        if price == 0:
            return {"error": "Не удалось найти цену (возможно, товар закончился)."}

        return {
            "shop": "Ситилинк",
            "name": name,
            "price": price,
            "currency": "₽",
            "image": image_url,
            "article": product_id,
            "url": url
        }