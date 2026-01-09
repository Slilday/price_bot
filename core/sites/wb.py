import re
from core.sites.base import BaseParser
import logging
logger = logging.getLogger(__name__)

class WbParser(BaseParser):
    def _get_article(self, url: str):
        match = re.search(r"catalog/(\d{6,15})", url)
        if match: return match.group(1)
        match_simple = re.search(r"/(\d{6,15})/", url)
        if match_simple: return match_simple.group(1)
        return None

    async def _find_host_and_json(self, vol, part, article):
        """Перебираем сервера basket-01...basket-32"""
        hosts = [f"basket-{i:02d}.wbbasket.ru" for i in range(1, 33)]
        for host in hosts:
            url = f"https://{host}/vol{vol}/part{part}/{article}/info/ru/card.json"
            data = await self.make_request(url, json=True, ignore_errors=True)
            if data:
                return host, data
        return None, None

    async def _get_price_from_search(self, article):
        """Запасной метод через поиск"""
        url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={article}&resultset=catalog"
        data = await self.make_request(url, json=True, ignore_errors=True)
        if data and data.get('data') and data['data'].get('products'):
            for prod in data['data']['products']:
                if str(prod.get('id')) == str(article):
                    # В поиске цена тоже может быть в sizes
                    price = prod.get('salePriceU') or prod.get('priceU') or 0
                    if price == 0 and prod.get('sizes'):
                        for size in prod['sizes']:
                            if size.get('price'):
                                price = size['price'].get('total') or size['price'].get('basic') or 0
                                if price > 0: break
                    return price / 100
        return 0

    async def parse(self, url: str):
        article_str = self._get_article(url)
        if not article_str:
            return {"error": "Неверная ссылка WB"}
        
        article = int(article_str)
        
        # 1. Card API
        api_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
        data = await self.make_request(api_url, json=True, ignore_errors=True)
        
        product_data = None
        if data and data.get('data') and data['data'].get('products'):
            product_data = data['data']['products'][0]

        price = 0
        name = "Товар Wildberries"
        
        if product_data:
            # 1.1. Смотрим цену наверху
            price_raw = product_data.get('salePriceU') or product_data.get('priceU') or 0
            
            # 1.2. Если 0 — смотрим внутри размеров (sizes)
            if price_raw == 0 and product_data.get('sizes'):
                for size in product_data['sizes']:
                    # Цена может быть в объекте 'price' внутри размера
                    if size.get('price'):
                        price_raw = size['price'].get('total') or size['price'].get('product') or size['price'].get('basic') or 0
                    if price_raw > 0:
                        break
            
            price = price_raw / 100
            name = product_data.get('name', name)

        # 2. Если всё еще 0 — пробуем через поиск
        if price == 0:
            price = await self._get_price_from_search(article)

        # 3. Ищем сервер для картинки и имени
        vol = article // 100000
        part = article // 1000
        host, json_data = await self._find_host_and_json(vol, part, article)
        
        if not host:
            # Если хост не найден, но цена есть (редко), ставим дефолтный
            if price > 0:
                host = "basket-01.wbbasket.ru"
            else:
                return {"error": "Товар не найден (возможно, удален)."}
            
        if name == "Товар Wildberries" and json_data:
            name = json_data.get('imt_name', name)

        image_url = f"https://{host}/vol{vol}/part{part}/{article}/images/big/1.jpg"
        
        logger.debug(f"WB_DEBUG: Артикул={article_str}, Цена={price}, Имя={name}, Картинка={image_url}")

        return {
            "shop": "Wildberries",
            "name": name,
            "price": price,
            "currency": "₽",
            "image": image_url,
            "article": str(article),
            "url": url
        }