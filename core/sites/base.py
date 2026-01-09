import aiohttp
from fake_useragent import UserAgent
from core.proxy_manager import proxy_manager
import logging

logger = logging.getLogger(__name__)

class BaseParser:
    def __init__(self):
        self.ua = UserAgent()

    async def make_request(self, url: str, json: bool = False, headers: dict = None, ignore_errors: bool = False):
        if headers is None:
            request_headers = {
                "User-Agent": self.ua.random,
                "Accept": "*/*"
            }
        else:
            request_headers = headers

        proxy = proxy_manager.get_proxy()

        async with aiohttp.ClientSession() as session:
            try:
                # ssl=False помогает избежать ошибок с сертификатами
                async with session.get(url, headers=request_headers, proxy=proxy, timeout=30, ssl=False) as response:
                    if response.status != 200:
                        if not ignore_errors:
                            logger.warning(f"⚠️ Ошибка запроса: код {response.status} на {url}")
                        return None
                    
                    if json:
                        return await response.json()
                    return await response.text()
            except Exception as e:
                if not ignore_errors:
                    logger.warning(f"⚠️ Ошибка соединения: {e} | URL: {url}")
                return None