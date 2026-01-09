import logging
import traceback
from urllib.parse import urlparse, urlunparse
from core.sites.wb import WbParser
from core.sites.steam import SteamParser
from core.sites.citilink import CitilinkParser
from core.sites.yandex import YandexParser
from core.sites.dns import DnsParser 

logger = logging.getLogger(__name__)

class ParserManager:
    def _clean_url(self, url: str):
        """Очищает URL от UTM-меток."""
        try:
            parsed = urlparse(url)
            # Собираем URL обратно без query (параметров после ?)
            cleaned_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
            if cleaned_url.endswith(';'):
                cleaned_url = cleaned_url[:-1]
            return cleaned_url
        except Exception:
            # Если не удалось очистить, возвращаем как есть
            return url

    def __init__(self):
        self.wb_parser = WbParser()
        self.steam_parser = SteamParser()
        self.citilink_parser = CitilinkParser()
        self.yandex_parser = YandexParser()
        self.dns_parser = DnsParser() 

        self.parsers = {
            "wildberries.ru": self.wb_parser,
            "www.wildberries.ru": self.wb_parser,
            "store.steampowered.com": self.steam_parser,
            "citilink.ru": self.citilink_parser,
            "www.citilink.ru": self.citilink_parser,
            "market.yandex.ru": self.yandex_parser,
            "m.market.yandex.ru": self.yandex_parser,
            "dns-shop.ru": self.dns_parser,
            "www.dns-shop.ru": self.dns_parser,
        }

    async def get_price(self, url: str):
        # Чистим URL
        cleaned_url = self._clean_url(url)
        logger.info(f"Обработка ссылки: {cleaned_url}")
        
        try:
            parsed_url = urlparse(cleaned_url)
            domain = parsed_url.netloc

            parser = self.parsers.get(domain)
            
            if not parser:
                # Ищем по частичному совпадению
                for key, p in self.parsers.items():
                    if key in domain:
                        parser = p
                        break
            
            if not parser:
                return {"error": f"Магазин {domain} не поддерживается."}
            
            # Запускаем парсер
            result = await parser.parse(cleaned_url)
            
            # Если успех, подменяем URL на чистый (без мусора)
            if result and "error" not in result:
                result['url'] = cleaned_url
            
            return result
            
        except Exception as e:
            # ЛОГИРУЕМ ПОЛНУЮ ОШИБКУ
            logger.error(f"Ошибка в ParserManager: {e}", exc_info=True)
            return {"error": f"Сбой парсинга: {type(e).__name__} - {e}"}