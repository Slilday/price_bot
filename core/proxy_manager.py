import random
import logging

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, proxy_file="proxies.txt"):
        self.proxies = []
        self.proxy_file = proxy_file
        self._load_proxies()

    def _load_proxies(self):
        """Загружает список прокси из файла."""
        try:
            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            
            if self.proxies:
                logger.info(f"✅ Загружено {len(self.proxies)} прокси.")
            else:
                logger.warning("⚠️ Файл с прокси пуст. Запросы будут идти с основного IP.")
        except FileNotFoundError:
            logger.warning(f"⚠️ Файл '{self.proxy_file}' не найден. Запросы будут идти с основного IP.")
            
    def get_proxy(self):
        """Возвращает случайный прокси из списка."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def get_proxy_count(self):
        """
        Возвращает количество прокси.
        Если список пуст, возвращаем 1 (наш собственный IP).
        """
        count = len(self.proxies)
        return count if count > 0 else 1

proxy_manager = ProxyManager()