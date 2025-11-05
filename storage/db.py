# storage/db.py
import sqlite3
import time
import os
from typing import Dict, List, Optional

class DB:
    def __init__(self, db_path: str = "/data/database.db"):
        # Создаем папку /data если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        # Создаем таблицу пользователей с новыми полями
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                telegram_username TEXT,
                nickname TEXT,
                password_hash TEXT,
                bananas INTEGER DEFAULT 0,
                per_click INTEGER DEFAULT 1,
                per_second INTEGER DEFAULT 0,
                last_update REAL DEFAULT 0,
                upgrades TEXT DEFAULT '{}',
                rebirths INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '{}',
                gold_expires REAL DEFAULT 0,
                active_banana_type TEXT DEFAULT '',
                active_banana_multiplier REAL DEFAULT 1.0,
                event_expires REAL DEFAULT 0,
                event_multiplier REAL DEFAULT 1.0,
                event_type TEXT DEFAULT ''
            )
        """)
        
        # Создаем таблицу активных ивентов
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS active_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                event_multiplier REAL,
                event_expires REAL
            )
        """)
        self.conn.commit()

    def create_user_if_not_exists(self, user_id: int, telegram_username: str):
        self.cur.execute(
            "INSERT OR IGNORE INTO users (user_id, telegram_username, last_update) VALUES (?, ?, ?)",
            (user_id, telegram_username, time.time())
        )
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        self.cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = self.cur.fetchone()
        if not row:
            return None
        
        columns = [col[0] for col in self.cur.description]
        user = dict(zip(columns, row))
        
        # Парсим JSON поля
        import json
        try:
            user['upgrades'] = json.loads(user.get('upgrades', '{}'))
        except:
            user['upgrades'] = {}
        
        try:
            user['inventory'] = json.loads(user.get('inventory', '{}'))
        except:
            user['inventory'] = {}
        
        return user

    def update_user(self, user_id: int, **kwargs):
        # Подготавливаем данные для обновления
        set_parts = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['upgrades', 'inventory']:
                # Сериализуем словари в JSON
                import json
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            values.append(value)
        
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(set_parts)} WHERE user_id = ?"
        try:
            self.cur.execute(query, values)
            self.conn.commit()
        except Exception as e:
            print(f"Error updating user {user_id}: {e}")
            raise e

    def all_users(self) -> List[Dict]:
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        columns = [col[0] for col in self.cur.description]
        
        users = []
        import json
        
        for row in rows:
            user = dict(zip(columns, row))
            
            # Парсим JSON поля
            try:
                user['upgrades'] = json.loads(user.get('upgrades', '{}'))
            except:
                user['upgrades'] = {}
            
            try:
                user['inventory'] = json.loads(user.get('inventory', '{}'))
            except:
                user['inventory'] = {}
            
            users.append(user)
        
        return users

    def get_inventory(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        return user.get('inventory', {}) if user else {}

    def use_from_inventory(self, user_id: int, item_type: str, amount: int = 1) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        
        inventory = user.get('inventory', {})
        current = inventory.get(item_type, 0)
        
        if current < amount:
            return False
        
        inventory[item_type] = current - amount
        if inventory[item_type] <= 0:
            del inventory[item_type]
        
        self.update_user(user_id, inventory=inventory)
        return True

    def start_event_for_all_users(self, event_name: str, multiplier: float, duration: int):
        expires = time.time() + duration
        
        # Обновляем всех пользователей
        users = self.all_users()
        for user in users:
            self.update_user(
                user['user_id'],
                event_expires=expires,
                event_multiplier=multiplier,
                event_type=event_name
            )
        
        # Сохраняем ивент в таблицу активных ивентов
        self.cur.execute(
            "INSERT INTO active_events (event_name, event_multiplier, event_expires) VALUES (?, ?, ?)",
            (event_name, multiplier, expires)
        )
        self.conn.commit()

    def check_and_remove_expired_events(self):
        current_time = time.time()
        
        # Удаляем просроченные ивенты из таблицы активных ивентов
        self.cur.execute("DELETE FROM active_events WHERE event_expires < ?", (current_time,))
        
        # Сбрасываем ивенты у пользователей, у которых истекло время
        self.cur.execute(
            "UPDATE users SET event_expires = 0, event_multiplier = 1.0, event_type = '' WHERE event_expires < ? AND event_expires > 0",
            (current_time,)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
