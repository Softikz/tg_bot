# storage/db.py
import sqlite3
import json
import time
import os
from typing import List, Dict

class DB:
    def __init__(self, path="/data/database.db"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        # Таблица пользователей
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
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
        
        self.conn.commit()

    def create_user_if_not_exists(self, user_id, username):
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        if not self.cur.fetchone():
            self.cur.execute(
                "INSERT INTO users (user_id, username, upgrades, last_update, inventory) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, "{}", time.time(), "{}")
            )
            self.conn.commit()

    def get_user(self, user_id) -> Dict:
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = self.cur.fetchone()
        if not row:
            return None
        user = dict(row)
        try:
            user["upgrades"] = json.loads(user.get("upgrades") or "{}")
            user["inventory"] = json.loads(user.get("inventory") or "{}")
        except Exception:
            user["upgrades"] = {}
            user["inventory"] = {}
        return user

    def update_user(self, user_id, **kwargs):
        if not kwargs:
            return
        
        self.conn.execute("BEGIN TRANSACTION")
        try:
            updates = []
            values = []
            for key, value in kwargs.items():
                if key in ["upgrades", "inventory"]:
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            self.cur.execute(query, values)
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise e

    def all_users(self) -> List[Dict]:
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        users = []
        for row in rows:
            user = dict(row)
            try:
                user["upgrades"] = json.loads(user.get("upgrades") or "{}")
                user["inventory"] = json.loads(user.get("inventory") or "{}")
            except Exception:
                user["upgrades"] = {}
                user["inventory"] = {}
            users.append(user)
        return users

    # Инвентарь методы
    def add_to_inventory(self, user_id: int, item: str, quantity: int = 1):
        user = self.get_user(user_id)
        if not user:
            return
        
        inventory = user.get("inventory", {})
        inventory[item] = inventory.get(item, 0) + quantity
        
        self.update_user(user_id, inventory=inventory)

    def use_from_inventory(self, user_id: int, item: str, quantity: int = 1):
        user = self.get_user(user_id)
        if not user:
            return False
        
        inventory = user.get("inventory", {})
        current_quantity = inventory.get(item, 0)
        
        if current_quantity < quantity:
            return False
        
        inventory[item] = current_quantity - quantity
        if inventory[item] == 0:
            del inventory[item]
        
        self.update_user(user_id, inventory=inventory)
        return True

    def get_inventory(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        return user.get("inventory", {}) if user else {}

    # Остальные методы без изменений
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
            DELETE FROM active_events 
            WHERE expires_at <= ?
        """, (current_time,))
        
        self.conn.commit()

    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()
