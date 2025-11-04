# storage/db.py
import sqlite3
import json
import time
import os
from typing import List, Dict, Optional


class DB:
    def __init__(self, path: str = "/data/database.db"):
        """
        Подключение к постоянной базе данных (в Railway сохраняется в /data)
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._create_tables()
        self.conn.commit()

    def _create_tables(self):
        """
        Создаёт таблицы, если их нет.
        """
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            telegram_username TEXT,
            nickname TEXT,
            password_hash TEXT,
            bananas INTEGER DEFAULT 0,
            per_click INTEGER DEFAULT 1,
            per_second INTEGER DEFAULT 0,
            upgrades TEXT DEFAULT '{}',
            last_update REAL DEFAULT 0,
            gold_expires REAL DEFAULT 0,
            rebirths INTEGER DEFAULT 0,
            event_expires REAL DEFAULT 0,
            event_multiplier REAL DEFAULT 1.0,
            event_type TEXT DEFAULT '',
            inventory TEXT DEFAULT '{}'
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS active_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            multiplier REAL,
            expires_at REAL,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
        """)

    # ---------- Пользователи ----------

    def create_user_if_not_exists(self, user_id: int, telegram_username: str):
        """
        Добавляет пользователя, если его нет.
        """
        self.cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
        if not self.cur.fetchone():
            now = time.time()
            self.cur.execute("""
                INSERT INTO users (user_id, telegram_username, upgrades, inventory, last_update)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, telegram_username, "{}", "{}", now))
            self.conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Возвращает данные пользователя (со всеми полями и JSON распаковкой).
        """
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = self.cur.fetchone()
        if not row:
            return None
        user = dict(row)
        # безопасная распаковка JSON
        for key in ["upgrades", "inventory"]:
            try:
                user[key] = json.loads(user.get(key) or "{}")
            except Exception:
                user[key] = {}
        return user

    def update_user(self, user_id: int, **kwargs):
        """
        Обновляет любые поля пользователя и сразу сохраняет в базу.
        """
        if not kwargs:
            return
        try:
            updates, values = [], []
            for key, value in kwargs.items():
                if key in ["upgrades", "inventory"]:
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            self.cur.execute(query, values)
            self.conn.commit()  # 💾 моментальное сохранение
        except Exception as e:
            self.conn.rollback()
            raise e

    def all_users(self) -> List[Dict]:
        """
        Возвращает всех пользователей (для фоновых задач).
        """
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        result = []
        for row in rows:
            user = dict(row)
            for key in ["upgrades", "inventory"]:
                try:
                    user[key] = json.loads(user.get(key) or "{}")
                except Exception:
                    user[key] = {}
            result.append(user)
        return result

    # ---------- Инвентарь ----------

    def add_to_inventory(self, user_id: int, item: str, quantity: int = 1):
        user = self.get_user(user_id)
        if not user:
            return
        inventory = user.get("inventory", {})
        inventory[item] = inventory.get(item, 0) + quantity
        self.update_user(user_id, inventory=inventory)

    def use_from_inventory(self, user_id: int, item: str, quantity: int = 1) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        inventory = user.get("inventory", {})
        if inventory.get(item, 0) < quantity:
            return False
        inventory[item] -= quantity
        if inventory[item] <= 0:
            del inventory[item]
        self.update_user(user_id, inventory=inventory)
        return True

    def get_inventory(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        return user.get("inventory", {}) if user else {}

    # ---------- Ивенты ----------

    def start_event_for_all_users(self, event_type: str, multiplier: float, duration_seconds: int):
        expires_at = time.time() + duration_seconds
        self.cur.execute("""
            UPDATE users
            SET event_expires = ?, event_multiplier = ?, event_type = ?
        """, (expires_at, multiplier, event_type))
        self.cur.execute("""
            INSERT INTO active_events (event_type, multiplier, expires_at)
            VALUES (?, ?, ?)
        """, (event_type, multiplier, expires_at))
        self.conn.commit()

    def check_and_remove_expired_events(self):
        current_time = time.time()
        self.cur.execute("""
            UPDATE users
            SET event_expires = 0, event_multiplier = 1.0, event_type = ''
            WHERE event_expires > 0 AND event_expires <= ?
        """, (current_time,))
        self.cur.execute("""
            DELETE FROM active_events WHERE expires_at <= ?
        """, (current_time,))
        self.conn.commit()

    def stop_all_events(self):
    """
    Останавливает все активные ивенты.
    """
    current_time = time.time()
    self.cur.execute("""
        UPDATE users 
        SET event_expires = 0, event_multiplier = 1.0, event_type = ''
        WHERE event_expires > ?
    """, (current_time,))
    self.cur.execute("DELETE FROM active_events")
    self.conn.commit()
    
    # ---------- Служебное ----------

    def close(self):
        if hasattr(self, "conn"):
            self.conn.commit()
            self.conn.close()

