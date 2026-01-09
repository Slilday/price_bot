import aiohttp
from fake_useragent import UserAgent
from core.proxy_manager import proxy_manager

class BaseParser:
    def __init__(self):
        self.ua = UserAgent()

    async def make_request(self, url: str, json: bool = False, ignore_errors: bool = False):
        """
        ignore_errors=True — не писать в консоль, если вернулась ошибка (404/500).
        """
        headers = {
            "User-Agent": self.ua.random,
            "Accept": "*/*"
        }
        proxy = proxy_manager.get_proxy()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, proxy=proxy, timeout=10) as response:
                    if response.status != 200:
                        if not ignore_errors:
                            print(f"⚠️ Ошибка запроса: код {response.status} на {url}")
                        return None
                    
                    if json:
                        return await response.json()
                    return await response.text()
            except Exception as e:
                if not ignore_errors:
                    print(f"⚠️ Ошибка соединения: {e}")
                return None