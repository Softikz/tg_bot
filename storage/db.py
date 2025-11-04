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
        inventory TEXT DEFAULT '{}',
        active_banana_type TEXT DEFAULT '',
        active_banana_multiplier REAL DEFAULT 1.0
    )
    """)
    # ... остальной код без изменений
