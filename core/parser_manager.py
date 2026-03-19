import logging
import traceback
from urllib.parse import urlparse, urlunparse

from core.sites.steam import SteamParser
from core.sites.citilink import CitilinkParser

logger = logging.getLogger(__name__)

class ParserManager:
    def _clean_url(self, url: str):
        """Очищает URL от UTM-меток."""
        try:
            parsed = urlparse(url)
            cleaned_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
            if cleaned_url.endswith(';'):
                cleaned_url = cleaned_url[:-1]
            return cleaned_url
        except Exception:
            return url

    def __init__(self):
        self.steam_parser = SteamParser()
        self.citilink_parser = CitilinkParser()

        self.parsers = {
            "store.steampowered.com": self.steam_parser,
            "citilink.ru": self.citilink_parser,
            "www.citilink.ru": self.citilink_parser,
        }

    async def get_price(self, url: str):
        cleaned_url = self._clean_url(url)
        logger.info(f"Обработка ссылки: {cleaned_url}")
        
        try:
            parsed_url = urlparse(cleaned_url)
            domain = parsed_url.netloc

            parser = self.parsers.get(domain)
            
            if not parser:
                for key, p in self.parsers.items():
                    if key in domain:
                        parser = p
                        break
            
            if not parser:
                return {"error": f"Магазин не поддерживается или ссылка неправильно написана"}

            result = await parser.parse(cleaned_url)

            if result and "error" not in result:
                result['url'] = cleaned_url
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка в ParserManager: {e}", exc_info=True)
            return {"error": f"Сбой парсинга: {type(e).__name__} - {e}"}