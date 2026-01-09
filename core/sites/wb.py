import re
import logging
from core.sites.base import BaseParser

logger = logging.getLogger(__name__)

class WbParser(BaseParser):
    def _get_article(self, url: str):
        match = re.search(r"catalog/(\d{6,15})", url)
        if match: return match.group(1)
        match_simple = re.search(r"/(\d{6,15})/", url)
        if match_simple: return match_simple.group(1)
        return None

    async def _find_host_and_json(self, vol, part, article):
        """Перебираем сервера basket-01...basket-32 для поиска данных."""
        hosts = [f"basket-{i:02d}.wbbasket.ru" for i in range(1, 33)]
        for host in hosts:
            url = f"https://{host}/vol{vol}/part{part}/{article}/info/ru/card.json"
            data = await self.make_request(url, json=True, ignore_errors=True)
            if data:
                return host, data
        return None, None

    async def parse(self, url: str):
        article_str = self._get_article(url)
        if not article_str:
            return {"error": "Неверная ссылка WB"}
        
        article = int(article_str)
        
        price = 0
        name = "Товар Wildberries"
        product_data = None

        mobile_headers = {
            'User-Agent': 'okhttp/4.11.0',
            'x-platform': 'android',
            'x-app-version': '5.20.0',
            'Accept': 'application/json',
        }

        # 1. Search API
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={article}&resultset=catalog"
        # === ИСПРАВЛЕНО: Передаем headers как именованный аргумент ===
        search_data = await self.make_request(url=search_url, json=True, headers=mobile_headers, ignore_errors=True)
        
        if search_data and isinstance(search_data, dict) and search_data.get('data'):
            products = search_data['data'].get('products')
            if products:
                for prod in products:
                    if str(prod.get('id')) == str(article):
                        product_data = prod
                        break
        
        # 2. Card API
        if not product_data:
            card_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
            card_data = await self.make_request(url=card_url, json=True, headers=mobile_headers, ignore_errors=True)
            if card_data and isinstance(card_data, dict) and card_data.get('data'):
                products = card_data['data'].get('products')
                if products:
                    product_data = products[0]
        
        # 3. Парсим
        if product_data and isinstance(product_data, dict):
            name = product_data.get('name', name)
            price_raw = product_data.get('salePriceU') or product_data.get('priceU') or 0
            
            if price_raw == 0 and product_data.get('sizes'):
                for size in product_data['sizes']:
                    if size and isinstance(size, dict) and size.get('price'):
                        price_raw = size['price'].get('total') or size['price'].get('basic') or 0
                        if price_raw > 0:
                            break
            
            price = price_raw / 100
        else:
            logger.warning(f"WB: Не удалось получить product_data для {article}")

        # 4. Ищем картинку и уточняем имя
        vol = article // 100000
        part = article // 1000
        host, json_data = await self._find_host_and_json(vol, part, article)
        
        if not host:
            if price > 0 or name != "Товар Wildberries":
                host = "basket-01.wbbasket.ru"
            else:
                return {"error": "Товар не найден."}
        
        if name == "Товар Wildberries" and json_data and isinstance(json_data, dict):
            name = json_data.get('imt_name', name)

        image_url = f"https://{host}/vol{vol}/part{part}/{article}/images/big/1.jpg"
        
        logger.debug(f"WB DEBUG: article={article}, price={price}, name='{name}'")

        if price == 0 and name == "Товар Wildberries":
             return {"error": "Не удалось получить данные (защита WB)."}
             
        return {
            "shop": "Wildberries",
            "name": name,
            "price": price,
            "currency": "₽",
            "image": image_url,
            "article": str(article),
            "url": url
        }