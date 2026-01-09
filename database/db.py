import aiosqlite
import time
from config import config

class Database:
    def __init__(self):
        self.db_path = config.DB_NAME

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    theme TEXT DEFAULT 'light', 
                    threshold REAL DEFAULT 5.0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    shop TEXT,
                    name TEXT,
                    article TEXT,
                    last_price REAL,
                    target_price REAL DEFAULT 0,
                    last_check REAL DEFAULT 0,
                    image_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
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

    async def add_user(self, user_id: int, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            await db.commit()

    async def add_item(self, user_id: int, url: str, shop: str, name: str, article: str, price: float, image: str | list):
        # === ЗАЩИТА ОТ СПИСКОВ ===
        # Если image пришел как список, берем первый элемент
        if isinstance(image, list):
            image = image[0] if len(image) > 0 else ""
        # =========================

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM items WHERE user_id = ? AND url = ?", (user_id, url))
            row = await cursor.fetchone()
            current_time = time.time()
            
            if row:
                item_id = row[0]
                await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, price))
                await db.execute("UPDATE items SET last_check = ? WHERE id = ?", (current_time, item_id))
                await db.commit()
                return item_id
            
            cursor = await db.execute("""
                INSERT INTO items (user_id, url, shop, name, article, last_price, last_check, image_url) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (user_id, url, shop, name, article, price, current_time, image))
            item_id = cursor.lastrowid
            await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, price))
            await db.commit()
            return item_id

    async def update_item_price(self, item_id: int, new_price: float):
        current_time = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE items SET last_price = ?, last_check = ? WHERE id = ?", (new_price, current_time, item_id))
            await db.execute("INSERT INTO price_history (item_id, price) VALUES (?, ?)", (item_id, new_price))
            await db.commit()

    async def update_last_check(self, item_id: int):
        current_time = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE items SET last_check = ? WHERE id = ?", (current_time, item_id))
            await db.commit()

    async def get_all_items(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items")
            return await cursor.fetchall()

    # ... (Остальные методы get_user_items, set_target_price и т.д. остаются без изменений из прошлого файла) ...
    # Скопируй их из предыдущего ответа, они там правильные.
    # Главное - новые методы update_last_check и измененный create_tables.
    
    # Чтобы ты не мучался, вот остальные методы списком:
    async def set_target_price(self, item_id: int, target_price: float):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM items WHERE id = ?", (item_id,))
            if not await cursor.fetchone(): return False
            await db.execute("UPDATE items SET target_price = ? WHERE id = ?", (target_price, item_id))
            await db.commit()
            return True
            
    async def set_user_threshold(self, user_id: int, threshold: float):
        async with aiosqlite.connect(self.db_path) as db:
            await self.add_user(user_id, "Unknown")
            await db.execute("UPDATE users SET threshold = ? WHERE user_id = ?", (threshold, user_id))
            await db.commit()

    async def get_user_threshold(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT threshold FROM users WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 5.0

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

    async def get_user_items_paginated(self, user_id: int, page: int = 1, page_size: int = 5):
        offset = (page - 1) * page_size
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE user_id = ? ORDER BY shop, name LIMIT ? OFFSET ?", (user_id, page_size, offset))
            items = await cursor.fetchall()
            cursor = await db.execute("SELECT COUNT(*) FROM items WHERE user_id = ?", (user_id,))
            total = (await cursor.fetchone())[0]
            return items, total

    async def get_item_by_id(self, item_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
                return await cursor.fetchone()

    async def get_price_history(self, url: str):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT h.date, h.price FROM price_history h JOIN items i ON h.item_id = i.id WHERE i.url = ? ORDER BY h.date ASC", (url,))
            return await cursor.fetchall()
            
    async def get_user_items(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE user_id = ?", (user_id,))
            return await cursor.fetchall()

    async def delete_item(self, user_id: int, url: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM items WHERE user_id = ? AND url = ?", (user_id, url))
            await db.commit()
            
    async def rename_item(self, item_id: int, new_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
            await db.commit()

db = Database()