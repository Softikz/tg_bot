# migrate_db.py
import sqlite3
import json
import time
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def migrate_database():
    """Безопасная миграция базы данных без потери данных"""
    
    # Подключаемся к существующей базе
    conn = sqlite3.connect('banana_bot.db')
    cur = conn.cursor()
    
    try:
        # Создаем временную таблицу с новой структурой
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users_new (
                user_id INTEGER PRIMARY KEY,
                telegram_username TEXT,
                nickname TEXT UNIQUE,
                password_hash TEXT,
                bananas REAL DEFAULT 0,
                per_click INTEGER DEFAULT 1,
                per_second REAL DEFAULT 0,
                upgrades TEXT DEFAULT '{}',
                rebirths INTEGER DEFAULT 0,
                last_update REAL DEFAULT 0,
                inventory TEXT DEFAULT '{}',
                active_bananas TEXT DEFAULT '{}',
                event_type TEXT DEFAULT '',
                event_multiplier REAL DEFAULT 1.0,
                event_expires REAL DEFAULT 0,
                created_at REAL DEFAULT 0
            )
        """)
        
        # Копируем данные из старой таблицы в новую
        cur.execute("""
            INSERT OR IGNORE INTO users_new 
            (user_id, telegram_username, nickname, password_hash, bananas, per_click, 
             per_second, upgrades, rebirths, last_update, inventory, 
             event_type, event_multiplier, event_expires, created_at)
            SELECT 
                user_id, telegram_username, nickname, password_hash, bananas, per_click,
                per_second, upgrades, rebirths, last_update, inventory,
                event_type, event_multiplier, event_expires, created_at
            FROM users
        """)
        
        # Переименовываем таблицы
        cur.execute("DROP TABLE IF EXISTS users_old")
        cur.execute("ALTER TABLE users RENAME TO users_old")
        cur.execute("ALTER TABLE users_new RENAME TO users")
        
        # Создаем остальные таблицы если их нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS active_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_multiplier REAL,
                expires_at REAL,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at REAL,
                expires_at REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        log.info("✅ Миграция базы данных успешно завершена!")
        
        # Проверяем данные
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        log.info(f"📊 Пользователей в базе: {user_count}")
        
        if user_count > 0:
            cur.execute("SELECT user_id, nickname FROM users LIMIT 5")
            users = cur.fetchall()
            log.info("👥 Последние пользователи:")
            for user_id, nickname in users:
                log.info(f"   - {nickname} (ID: {user_id})")
        
    except Exception as e:
        log.error(f"❌ Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
