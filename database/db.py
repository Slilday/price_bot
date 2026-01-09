import aiosqlite
from config import config

class Database:
    def __init__(self):
        self.db_path = config.DB_NAME

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей с темой и порогом (ЕДИНАЯ ВЕРСИЯ)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    theme TEXT DEFAULT 'light', 
                    threshold REAL DEFAULT 5.0,  -- Порог в %, по умолчанию 5%
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица товаров
            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    shop TEXT,
                    name TEXT,
                    article TEXT,
                    last_price REAL,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица истории цен
            await db.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    price REAL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES items(id)
                )
            """)
            await db.commit()


    # === МЕТОДЫ, КОТОРЫЕ БЫЛИ СНАРУЖИ, ТЕПЕРЬ ВНУТРИ ===
    async def set_user_threshold(self, user_id: int, threshold: float):
        """Установить глобальный порог уведомлений в %."""
        async with aiosqlite.connect(self.db_path) as db:
            await self.add_user(user_id, "Unknown")
            await db.execute("UPDATE users SET threshold = ? WHERE user_id = ?", (threshold, user_id))
            await db.commit()

    async def get_user_threshold(self, user_id: int):
        """Получить порог пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT threshold FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 5.0
    # =======================================================


    async def add_user(self, user_id: int, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            await db.commit()

    async def set_user_theme(self, user_id: int, theme: str):
        async with aiosqlite.connect(self.db_path) as db:
            await self.add_user(user_id, "Unknown") 
            await db.execute("UPDATE users SET theme = ? WHERE user_id = ?", (theme, user_id))
            await db.commit()

    async def get_user_theme(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT theme FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 'light'

    async def add_item(self, user_id: int, url: str, shop: str, name: str, article: str, price: float, image: str):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM items WHERE user_id = ? AND url = ?", (user_id, url))
            existing = await cursor.fetchone()
            
            if existing:
                item_id = existing[0]
                await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, price))
                await db.commit()
                return item_id

            cursor = await db.execute("""
                INSERT INTO items (user_id, url, shop, name, article, last_price, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, url, shop, name, article, price, image))
            
            item_id = cursor.lastrowid
            await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, price))
            await db.commit()
            return item_id

    async def get_user_items(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
            return rows

    async def get_item_by_id(self, item_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
                return await cursor.fetchone()

    async def delete_item(self, user_id: int, url: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM items WHERE user_id = ? AND url = ?", (user_id, url))
            await db.commit()

    async def get_price_history(self, url: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT h.date, h.price
                FROM price_history h
                JOIN items i ON h.item_id = i.id
                WHERE i.url = ?
                ORDER BY h.date ASC
            """
            cursor = await db.execute(query, (url,))
            return await cursor.fetchall()

    async def get_all_items(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM items") as cursor:
                return await cursor.fetchall()

    async def update_item_price(self, item_id: int, new_price: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE items SET last_price = ? WHERE id = ?", (new_price, item_id))
            await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, new_price))
            await db.commit()
    
    async def get_user_items_paginated(self, user_id: int, page: int = 1, page_size: int = 5):
        offset = (page - 1) * page_size
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM items WHERE user_id = ? ORDER BY shop, name LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            )
            items = await cursor.fetchall()
            cursor = await db.execute("SELECT COUNT(*) FROM items WHERE user_id = ?", (user_id,))
            total_items = (await cursor.fetchone())[0]
            return items, total_items
    
    async def rename_item(self, item_id: int, new_name: str):
        """Изменяет имя товара по его ID."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
            await db.commit()

db = Database()