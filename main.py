# main.py
import asyncio
import logging
import signal
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain

# Токен бота
API_TOKEN = "8226054487:AAEiJz0n9FgOpSk62QXpgHWGGFdGjxsy9es"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def passive_income_loop(db: DB, interval: int = 5):
    """Фоновая задача для пассивного дохода"""
    logger.info("🟢 Passive income loop started")
    while True:
        try:
            rows = db.all_users()
            for user in rows:
                added, new_last = apply_offline_gain(user)
                if added:
                    new_bananas = user.get("bananas", 0) + added
                    db.update_user(user["user_id"], bananas=new_bananas, last_update=new_last)
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception("Error in passive_income_loop: %s", e)
            await asyncio.sleep(10)

async def event_checker_loop(db: DB, interval: int = 60):
    """Фоновая задача для проверки ивентов"""
    logger.info("🟢 Event checker loop started")
    while True:
        try:
            db.check_and_remove_expired_events()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception("Error in event_checker_loop: %s", e)
            await asyncio.sleep(60)

async def database_health_check(db: DB, interval: int = 300):
    """Периодическая проверка здоровья базы данных"""
    logger.info("🟢 Database health check started")
    while True:
        try:
            stats = db.get_database_stats()
            logger.info(f"📊 Статистика БД: {stats['user_count']} пользователей, {stats['total_bananas']} бананов, размер: {stats['database_size']} байт")
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception("Error in database_health_check: %s", e)
            await asyncio.sleep(300)

async def main():
    logger.info("🚀 Бот запускается...")
    
    # Логируем системную информацию
    logger.info("=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===")
    logger.info(f"Текущая директория: {os.getcwd()}")
    logger.info("Содержимое директории:")
    for file in os.listdir():
        logger.info(f"  - {file}")
    
    # Инициализация базы данных
    try:
        db = DB()
        
        # Логируем начальную статистику
        stats = db.get_database_stats()
        logger.info(f"📦 База данных загружена: {stats['user_count']} пользователей, {stats['total_bananas']} бананов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        return

    # Инициализация бота
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Подключаем роутер
    dp.include_router(router)
    
    logger.info("✅ Роутер подключен")

    # Запуск фоновых задач
    passive_task = asyncio.create_task(passive_income_loop(db))
    event_task = asyncio.create_task(event_checker_loop(db))
    health_task = asyncio.create_task(database_health_check(db))
    
    logger.info("✅ Фоновые задачи запущены")

    # Обработка сигналов для корректной остановки
    stop_event = asyncio.Event()

    def signal_handler():
        """Обработчик сигналов остановки"""
        logger.info("🛑 Получен сигнал остановки...")
        stop_event.set()

    # Регистрируем обработчики сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            logger.warning(f"Сигнал {sig} не поддерживается на этой платформе")

    try:
        logger.info("🔗 Подключаемся к Telegram...")
        
        # Создаем резервную копию перед запуском
        try:
            backup_path = db.backup_database()
            logger.info(f"💾 Резервная копия создана: {backup_path}")
        except Exception as e:
            logger.warning(f"Не удалось создать резервную копию: {e}")
        
        # Останавливаем предыдущий webhook если был
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling
        logger.info("🔄 Запускаем polling...")
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=False
        )
        
    except asyncio.CancelledError:
        logger.info("📦 Polling отменен")
    except Exception as e:
        logger.exception("❌ Ошибка в polling: %s", e)
    finally:
        # Корректная остановка
        logger.info("🧹 Останавливаем бота...")
        
        # Создаем финальную резервную копию
        try:
            backup_path = db.backup_database()
            logger.info(f"💾 Финальная резервная копия: {backup_path}")
        except Exception as e:
            logger.warning(f"Не удалось создать финальную резервную копию: {e}")
        
        # Отменяем фоновые задачи
        passive_task.cancel()
        event_task.cancel()
        health_task.cancel()
        
        # Ждем завершения задач
        try:
            await asyncio.gather(passive_task, event_task, health_task, return_exceptions=True)
        except Exception as e:
            logger.debug("Фоновые задачи завершены: %s", e)
        
        # Логируем финальную статистику
        try:
            final_stats = db.get_database_stats()
            logger.info(f"📊 Финальная статистика: {final_stats['user_count']} пользователей, {final_stats['total_bananas']} бананов")
        except Exception as e:
            logger.warning(f"Не удалось получить финальную статистику: {e}")
        
        # Закрываем соединения
        await bot.session.close()
        db.close()
        
        logger.info("✅ Бот полностью остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.exception("💥 Критическая ошибка: %s", e)
