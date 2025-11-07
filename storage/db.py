# storage/db.py
import sqlite3
import json
import time
import logging
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)

class DB:
    def __init__(self, db_path="banana_bot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Таблица пользователей
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
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
        
        # Таблица активных ивентов
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS active_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_multiplier REAL,
                expires_at REAL,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        
        # Таблица сессий (для будущего использования)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at REAL,
                expires_at REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        self.conn.commit()

    def create_user_if_not_exists(self, user_id: int, telegram_username: str = "unknown"):
        """Создает пользователя если он не существует с полными начальными данными"""
        try:
            current_time = time.time()
            # Создаем пользователя со всеми необходимыми полями
            self.cur.execute(
                """INSERT OR IGNORE INTO users 
                (user_id, telegram_username, bananas, per_click, per_second, upgrades, 
                 rebirths, last_update, inventory, active_bananas, event_type, 
                 event_multiplier, event_expires, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, telegram_username, 0, 1, 0, '{}', 0, current_time, 
                 '{}', '{}', '', 1.0, 0, current_time)
            )
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error creating user {user_id}: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя по ID"""
        try:
            self.cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = self.cur.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in self.cur.description]
            user = dict(zip(columns, row))
            
            # Парсим JSON поля
            for field in ['upgrades', 'inventory', 'active_bananas']:
                if user.get(field):
                    try:
                        user[field] = json.loads(user[field])
                    except:
                        user[field] = {}
                else:
                    user[field] = {}
            
            return user
        except Exception as e:
            log.error(f"Error getting user {user_id}: {e}")
            return None

    def update_user(self, user_id: int, **kwargs):
        """Обновляет данные пользователя"""
        try:
            # Обрабатываем JSON поля
            for field in ['upgrades', 'inventory', 'active_bananas']:
                if field in kwargs and isinstance(kwargs[field], (dict, list)):
                    kwargs[field] = json.dumps(kwargs[field])
            
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(user_id)
            
            query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
            self.cur.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error updating user {user_id}: {e}")
            return False

    def all_users(self) -> List[Dict]:
        """Получает всех пользователей"""
        try:
            self.cur.execute("SELECT * FROM users")
            rows = self.cur.fetchall()
            columns = [desc[0] for desc in self.cur.description]
            
            users = []
            for row in rows:
                user = dict(zip(columns, row))
                
                # Парсим JSON поля
                for field in ['upgrades', 'inventory', 'active_bananas']:
                    if user.get(field):
                        try:
                            user[field] = json.loads(user[field])
                        except:
                            user[field] = {}
                    else:
                        user[field] = {}
                
                users.append(user)
            
            return users
        except Exception as e:
            log.error(f"Error getting all users: {e}")
            return []

    def get_user_by_nickname(self, nickname: str) -> Optional[Dict]:
        """Получает пользователя по никнейму"""
        try:
            self.cur.execute("SELECT * FROM users WHERE nickname = ?", (nickname,))
            row = self.cur.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in self.cur.description]
            user = dict(zip(columns, row))
            
            # Парсим JSON поля
            for field in ['upgrades', 'inventory', 'active_bananas']:
                if user.get(field):
                    try:
                        user[field] = json.loads(user[field])
                    except:
                        user[field] = {}
                else:
                    user[field] = {}
            
            return user
        except Exception as e:
            log.error(f"Error getting user by nickname {nickname}: {e}")
            return None

    def is_nickname_taken(self, nickname: str) -> bool:
        """Проверяет, занят ли никнейм"""
        user = self.get_user_by_nickname(nickname)
        return user is not None

    def start_event_for_all_users(self, event_type: str, multiplier: float, duration_seconds: int):
        """Запускает ивент для всех пользователей"""
        try:
            expires_at = time.time() + duration_seconds
            
            # Обновляем всех пользователей
            self.cur.execute(
                "UPDATE users SET event_type = ?, event_multiplier = ?, event_expires = ?",
                (event_type, multiplier, expires_at)
            )
            
            # Добавляем запись в таблицу активных ивентов
            self.cur.execute(
                "INSERT INTO active_events (event_type, event_multiplier, expires_at) VALUES (?, ?, ?)",
                (event_type, multiplier, expires_at)
            )
            
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error starting event for all users: {e}")
            return False

    def get_active_events(self) -> List[Dict]:
        """Получает активные ивенты"""
        try:
            current_time = time.time()
            self.cur.execute(
                "SELECT * FROM active_events WHERE expires_at > ?",
                (current_time,)
            )
            rows = self.cur.fetchall()
            columns = [desc[0] for desc in self.cur.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            log.error(f"Error getting active events: {e}")
            return []

    def check_and_remove_expired_events(self):
        """Проверяет и удаляет просроченные ивенты (альяс для cleanup_expired_events)"""
        self.cleanup_expired_events()

    def cleanup_expired_events(self):
        """Очищает просроченные ивенты"""
        try:
            current_time = time.time()
            
            # Сбрасываем ивенты у пользователей
            self.cur.execute(
                "UPDATE users SET event_type = '', event_multiplier = 1.0, event_expires = 0 WHERE event_expires > 0 AND event_expires < ?",
                (current_time,)
            )
            
            # Удаляем просроченные ивенты
            self.cur.execute(
                "DELETE FROM active_events WHERE expires_at < ?",
                (current_time,)
            )
            
            self.conn.commit()
            log.info("Expired events cleaned up successfully")
        except Exception as e:
            log.error(f"Error cleaning up expired events: {e}")

    def cleanup_expired_bananas(self):
        """Очищает просроченные бананы"""
        try:
            current_time = time.time()
            
            # Получаем всех пользователей с активными бананами
            users = self.all_users()
            cleaned_count = 0
            
            for user in users:
                active_bananas = user.get("active_bananas", {})
                if active_bananas:
                    updated_bananas = {}
                    for banana_type, expires in active_bananas.items():
                        if expires > current_time:
                            updated_bananas[banana_type] = expires
                    
                    if len(updated_bananas) != len(active_bananas):
                        self.update_user(user["user_id"], active_bananas=updated_bananas)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                log.info(f"Cleaned expired bananas for {cleaned_count} users")
            
        except Exception as e:
            log.error(f"Error cleaning up expired bananas: {e}")

    def get_user_count(self) -> int:
        """Возвращает количество пользователей"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM users")
            return self.cur.fetchone()[0]
        except Exception as e:
            log.error(f"Error getting user count: {e}")
            return 0

    def get_total_bananas(self) -> float:
        """Возвращает общее количество бананов"""
        try:
            self.cur.execute("SELECT SUM(bananas) FROM users")
            result = self.cur.fetchone()[0]
            return result if result else 0
        except Exception as e:
            log.error(f"Error getting total bananas: {e}")
            return 0

    def get_total_rebirths(self) -> int:
        """Возвращает общее количество перерождений"""
        try:
            self.cur.execute("SELECT SUM(rebirths) FROM users")
            result = self.cur.fetchone()[0]
            return result if result else 0
        except Exception as e:
            log.error(f"Error getting total rebirths: {e}")
            return 0

    def get_recent_users(self, hours: int = 24) -> List[Dict]:
        """Получает пользователей, зарегистрированных за последние N часов"""
        try:
            time_threshold = time.time() - (hours * 3600)
            self.cur.execute(
                "SELECT * FROM users WHERE created_at > ? ORDER BY created_at DESC",
                (time_threshold,)
            )
            rows = self.cur.fetchall()
            columns = [desc[0] for desc in self.cur.description]
            
            users = []
            for row in rows:
                user = dict(zip(columns, row))
                
                # Парсим JSON поля
                for field in ['upgrades', 'inventory', 'active_bananas']:
                    if user.get(field):
                        try:
                            user[field] = json.loads(user[field])
                        except:
                            user[field] = {}
                    else:
                        user[field] = {}
                
                users.append(user)
            
            return users
        except Exception as e:
            log.error(f"Error getting recent users: {e}")
            return []

    def close(self):
        """Закрывает соединение с базой данных"""
        self.conn.close()
