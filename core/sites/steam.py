import re
from core.sites.base import BaseParser

class SteamParser(BaseParser):
    def _get_app_id(self, url: str):
        """Вытаскиваем ID игры из ссылки"""
        match = re.search(r"app/(\d+)", url)
        if match:
            return match.group(1)
        return None

    async def parse(self, url: str):
        app_id = self._get_app_id(url)
        if not app_id:
            return {"error": "Не удалось найти ID игры. Убедитесь, что ссылка ведет на store.steampowered.com/app/..."}

        api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=ru&l=russian"
        
        data = await self.make_request(api_url, json=True)
        
        if not data or str(app_id) not in data:
            return {"error": "Steam не вернул данные."}

        game_data = data[str(app_id)]
        
        if not game_data.get("success"):
            return {"error": "Игры с таким ID не существует или она недоступна в регионе RU."}

        details = game_data.get("data", {})
        
        name = details.get("name", "Неизвестная игра")
        image = details.get("header_image", "")
        
        # Обработка цены
        price = 0
        currency = "RUB"
        
        if details.get("is_free"):
            price = 0
        elif "price_overview" in details:
            price_data = details["price_overview"]
            price = price_data.get("final", 0) / 100
            currency = "₽"
        else:
            price = 0

        return {
            "shop": "Steam",
            "name": name,
            "price": price,
            "currency": currency,
            "image": image,
            "article": app_id,
            "url": url
        }