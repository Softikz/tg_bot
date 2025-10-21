import sqlite3
import json
import time

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
            gold_expires REAL DEFAULT 0
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

    def get_user(self, user_id):
        self.cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = self.cur.fetchone()
        if not row:
            return None
        user = dict(row)
        user["upgrades"] = json.loads(user["upgrades"])
        return user

    def update_user(self, user_id, **kwargs):
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

    def all_users(self):
        self.cur.execute("SELECT * FROM users")
        rows = self.cur.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self.conn.close()
