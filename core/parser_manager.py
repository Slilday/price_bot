from urllib.parse import urlparse
from core.sites.wb import WbParser
from core.sites.steam import SteamParser
from core.sites.citilink import CitilinkParser # <--- Импорт

class ParserManager:
    def __init__(self):
        self.wb_parser = WbParser()
        self.steam_parser = SteamParser()
        self.citilink_parser = CitilinkParser() # <--- Экземпляр

        self.parsers = {
            # Wildberries
            "wildberries.ru": self.wb_parser,
            "www.wildberries.ru": self.wb_parser,
            
            # Steam
            "store.steampowered.com": self.steam_parser,
            "steamcommunity.com": self.steam_parser,
            
            # Citilink
            "citilink.ru": self.citilink_parser,
            "www.citilink.ru": self.citilink_parser,
        }

    async def get_price(self, url: str):
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            parser = self.parsers.get(domain)
            
            if not parser:
                for key, p in self.parsers.items():
                    if key in domain:
                        parser = p
                        break
            
            if not parser:
                return {"error": "Я пока не умею работать с этим магазином :("}

            return await parser.parse(url)
            
        except Exception as e:
            return {"error": f"Ошибка обработки ссылки: {e}"}