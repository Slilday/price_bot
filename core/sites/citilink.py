import re
import json
import logging
from bs4 import BeautifulSoup
from core.sites.base import BaseParser

logger = logging.getLogger(__name__)

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

        html = await self.make_request(url, json=False)
        
        if not html:
            return {"error": "Ситилинк не открывается (возможно, блокировка IP)."}

        soup = BeautifulSoup(html, "html.parser")

        name = "Товар Ситилинк"
        price = 0
        image_url = ""

        # === СТРАТЕГИЯ 1: JSON-LD ===
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                if not script.string: continue
                data = json.loads(script.string)
                
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items:
                    if item.get("@type") == "Product":
                        name = item.get("name", name)
                        
                        # ОБРАБОТКА КАРТИНКИ 
                        img_data = item.get("image")
                        if img_data:
                            if isinstance(img_data, str):
                                image_url = img_data
                            elif isinstance(img_data, list) and len(img_data) > 0:
                                first = img_data[0]
                                if isinstance(first, str):
                                    image_url = first
                                elif isinstance(first, dict):
                                    image_url = first.get('url') or first.get('contentUrl')
                            elif isinstance(img_data, dict):
                                # Если словарь {'url': '...', ...}
                                image_url = img_data.get('url') or img_data.get('contentUrl')
                        # ---------------------------------------
                        
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            price = float(offers.get("price", 0))
                        elif isinstance(offers, list) and offers:
                            price = float(offers[0].get("price", 0))
                        
                        if price > 0: break
                if price > 0: break
            except:
                continue

        if price == 0:
            try:
                price_meta = soup.find("meta", {"itemprop": "price"})
                if price_meta:
                    price = float(price_meta.get("content"))
            except: pass

        if name == "Товар Ситилинк":
            h1 = soup.find("h1")
            if h1: name = h1.get_text(strip=True)

        if not image_url:
            img_meta = soup.find("meta", {"property": "og:image"})
            if img_meta: image_url = img_meta.get("content")

        if not isinstance(image_url, str):
            image_url = ""

        if price == 0:
            return {"error": "Цена не найдена (возможно, блокировка)."}

        return {
            "shop": "Ситилинк",
            "name": name,
            "price": price,
            "currency": "₽",
            "image": image_url,
            "article": product_id,
            "url": url
        }