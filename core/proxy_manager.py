import random

class ProxyManager:
    def __init__(self):
        # Сюда можно будет добавить список прокси
        # Пример: ["http://user:pass@ip:port", ...]
        self.proxies = []

    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

# Создаем один объект, чтобы использовать его везде
proxy_manager = ProxyManager()