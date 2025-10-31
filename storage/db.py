# storage/db.py
import sqlite3
import json
import time
from typing import List, Dict, Optional

class DB:
    def __init__(self, path="database.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

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
            rebirths INTEGER DEFAULT 0
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            multiplier REAL,
            expires REAL
        )
        """)

        self.conn.commit()

    # ======== USERS ========
    def create_user_if_not_exists(self, user_id, username):
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        if not self.cur.fetchone():
            self.cur.execute(
                "INSERT INTO users (user_id, username, upgrades, last_update) VALUES (?, ?, ?, ?)",
                (user_id, username, "{}", time.time())
            )
            self.conn.commit()

    def get_user(self, user_id) -> Optional[Dict]:
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
        updates, values = [], []
        for key, value in kwargs.items():
            if key == "upgrades":
                value = json.dumps(value)
            updates.append(f"{key}=?")
            values.append(value)
        values.append(user_id)
        self.cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id=?", values)
        self.conn.commit()

    def all_users(self) -> List[Dict]:
        self.cur.execute("SELECT * FROM users")
        return [dict(row) for row in self.cur.fetchall()]

    # ======== EVENTS ========
    def get_active_event(self) -> Optional[Dict]:
        self.cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT 1")
        row = self.cur.fetchone()
        if not row:
            return None
        event = dict(row)
        if event["expires"] > time.time():
            return event
        else:
            self.clear_event()
            return None

    def set_event(self, type_: str, multiplier: float, expires: float):
        self.cur.execute("DELETE FROM events")
        self.cur.execute("INSERT INTO events (type, multiplier, expires) VALUES (?, ?, ?)", (type_, multiplier, expires))
        self.conn.commit()

    def clear_event(self):
        self.cur.execute("DELETE FROM events")
        self.conn.commit()

    def close(self):
        self.conn.close()
