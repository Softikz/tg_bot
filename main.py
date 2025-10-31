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

async def passive_income_loop(db: DB, interval: int = 1):
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
            await asyncio.sleep(5)

async def event_checker_loop(db: DB, interval: int = 30):
    """Проверка активных ивентов"""
    logger.info("🟢 Event checker loop started")
    while True:
        try:
            # УБРАЛ AWAIT - метод синхронный
            db.check_and_remove_expired_events()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception("Error in event_checker_loop: %s", e)
            await asyncio.sleep(60)

async def main():
    logger.info("🚀 Бот запускается...")
    
    db = DB()
    
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Подключаем роутер
    dp.include_router(router)
    
    logger.info(f"Бот запущен. Роутер подключен.")

    # Запуск фоновых задач
    asyncio.create_task(passive_income_loop(db))
    asyncio.create_task(event_checker_loop(db))

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Polling error: %s", e)
    finally:
        await bot.session.close()
        db.close()
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
