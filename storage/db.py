import sqlite3
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class DB:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица чатов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER PRIMARY KEY,
                        chat_type TEXT,
                        title TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица сообщений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        chat_id INTEGER,
                        text TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")

    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление пользователя в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                logger.debug(f"User {user_id} added/updated in database")
                
        except sqlite3.Error as e:
            logger.error(f"Error adding user {user_id}: {e}")

    def add_chat(self, chat_id: int, chat_type: str, title: str = None):
        """Добавление чата в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO chats (chat_id, chat_type, title)
                    VALUES (?, ?, ?)
                ''', (chat_id, chat_type, title))
                conn.commit()
                logger.debug(f"Chat {chat_id} added/updated in database")
                
        except sqlite3.Error as e:
            logger.error(f"Error adding chat {chat_id}: {e}")

    def add_message(self, user_id: int, chat_id: int, text: str):
        """Добавление сообщения в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (user_id, chat_id, text)
                    VALUES (?, ?, ?)
                ''', (user_id, chat_id, text))
                conn.commit()
                logger.debug(f"Message from user {user_id} added to database")
                
        except sqlite3.Error as e:
            logger.error(f"Error adding message from user {user_id}: {e}")

    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Получение информации о пользователе"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                return cursor.fetchone()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    def get_chat(self, chat_id: int) -> Optional[Tuple]:
        """Получение информации о чате"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
                return cursor.fetchone()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting chat {chat_id}: {e}")
            return None

    def all_users(self):
        """Получение всех пользователей (аналог get_all_users)"""
        return self.get_all_users()

    def check_and_remove_expired_events(self):
        """Проверка и удаление истекших событий"""
        # Этот метод нужно реализовать в зависимости от вашей структуры событий
        # Вот базовая реализация:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу событий если её нет
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        event_type TEXT,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Удаляем истекшие события
                cursor.execute('DELETE FROM events WHERE expires_at < CURRENT_TIMESTAMP')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Removed {deleted_count} expired events")
                
                return deleted_count
                    
        except sqlite3.Error as e:
            logger.error(f"Error checking expired events: {e}")
            return 0
    
    def get_user_messages(self, user_id: int, limit: int = 10) -> List[Tuple]:
        """Получение последних сообщений пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM messages 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
            return []

    def get_chat_messages(self, chat_id: int, limit: int = 10) -> List[Tuple]:
        """Получение последних сообщений в чате"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM messages 
                    WHERE chat_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (chat_id, limit))
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting messages for chat {chat_id}: {e}")
            return []

    def get_all_users(self) -> List[Tuple]:
        """Получение списка всех пользователей"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users ORDER BY registered_at DESC')
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_all_chats(self) -> List[Tuple]:
        """Получение списка всех чатов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM chats ORDER BY created_at DESC')
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all chats: {e}")
            return []

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя и его сообщений"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Сначала удаляем сообщения пользователя
                cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
                # Затем удаляем самого пользователя
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
                logger.info(f"User {user_id} and their messages deleted")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    def get_statistics(self) -> dict:
        """Получение статистики базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM users')
                users_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM chats')
                chats_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM messages')
                messages_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM messages')
                active_users = cursor.fetchone()[0]
                
                return {
                    'users_count': users_count,
                    'chats_count': chats_count,
                    'messages_count': messages_count,
                    'active_users': active_users
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


