# storage/db.py
import sqlite3
import json
import time
import os
from typing import List, Dict

class DB:
    def __init__(self, path="database.db"):
        # Используем абсолютный путь для Railway
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Создание таблиц если они не существуют"""
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
            event_type TEXT DEFAULT ''
        )
        """)
        
        # Таблица активных ивентов (для админских функций)
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
                "INSERT INTO users (user_id, username, upgrades, last_update) VALUES (?, ?, ?, ?)",
                (user_id, username, "{}", time.time())
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
        except Exception:
            user["upgrades"] = {}
        return user

    def update_user(self, user_id, **kwargs):
        if not kwargs:
            return
        updates = []
        values = []
        for key, value in kwargs.items():
            if key == "upgrades":
                value = json.dumps(value)
            updates.append(f"{key} = ?")
            values.append(value)
        values.append(user_id)
        self.cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", values)
        self.conn.commit()

    def all_users(self) -> List[Dict]:
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        return [dict(row) for row in rows]

    def get_all_users(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT user_id, username FROM users")
        rows = cur.fetchall()
        return [{"user_id": r[0], "username": r[1]} for r in rows]

    def reset_user_progress(self, user_id: int):
        self.cur.execute("""
            UPDATE users
            SET bananas=0,
                per_click=1,
                per_second=0,
                upgrades='{}'
            WHERE user_id=?
        """, (user_id,))
        self.conn.commit()

    def add_gold_banana(self, user_id: int):
        user = self.get_user(user_id)
        if not user:
            return
        gold_expires = max(time.time(), user.get("gold_expires", 0)) + 86400
        self.update_user(user_id, gold_expires=gold_expires)

    def add_passive_clicks(self, user_id: int, amount: int = 2):
        user = self.get_user(user_id)
        if not user:
            return
        self.update_user(user_id, per_second=user.get("per_second", 0) + amount)

    def add_bananas(self, user_id: int, amount: int):
        user = self.get_user(user_id)
        if not user:
            return
        self.update_user(user_id, bananas=user.get("bananas", 0) + amount)

    # Новые методы для работы с ивентами
    def start_event_for_all_users(self, event_type: str, multiplier: float, duration_seconds: int):
        """Запустить ивент для всех пользователей"""
        expires_at = time.time() + duration_seconds
        
        # Обновляем всех пользователей
        self.cur.execute("""
            UPDATE users 
            SET event_expires = ?, event_multiplier = ?, event_type = ?
        """, (expires_at, multiplier, event_type))
        
        # Сохраняем ивент в таблицу активных ивентов
        self.cur.execute("""
            INSERT INTO active_events (event_type, multiplier, expires_at)
            VALUES (?, ?, ?)
        """, (event_type, multiplier, expires_at))
        
        self.conn.commit()

    def check_and_remove_expired_events(self):
        """Проверить и удалить истекшие ивенты"""
        current_time = time.time()
        
        # Находим пользователей с истекшими ивентами
        self.cur.execute("""
            SELECT user_id FROM users 
            WHERE event_expires > 0 AND event_expires <= ?
        """, (current_time,))
        
        expired_users = self.cur.fetchall()
        
        if expired_users:
            # Сбрасываем ивенты для этих пользователей
            self.cur.execute("""
                UPDATE users 
                SET event_expires = 0, event_multiplier = 1.0, event_type = ''
                WHERE event_expires > 0 AND event_expires <= ?
            """, (current_time,))
            
            # Удаляем истекшие ивенты из таблицы активных ивентов
            self.cur.execute("""
                DELETE FROM active_events 
                WHERE expires_at <= ?
            """, (current_time,))
            
            self.conn.commit()
            print(f"Сброшены ивенты для {len(expired_users)} пользователей")

    def get_active_event(self):
        """Получить текущий активный ивент"""
        self.cur.execute("""
            SELECT * FROM active_events 
            WHERE expires_at > ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (time.time(),))
        
        row = self.cur.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()
