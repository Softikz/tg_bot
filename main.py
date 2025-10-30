# main.py
import asyncio
import logging
import signal
import os
from aiogram import Bot, Dispatcher
from handlers.commands import register_handlers
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

async def main():
    logger.info("🚀 Бот запускается...")
    
    # Логируем информацию о версии и файлах
    logger.info("=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===")
    logger.info(f"Текущая директория: {os.getcwd()}")
    logger.info("Содержимое директории:")
    for file in os.listdir():
        logger.info(f"  - {file}")
    
    if os.path.exists("handlers"):
        logger.info("Содержимое handlers:")
        for file in os.listdir("handlers"):
            logger.info(f"  - {file}")
    
    logger.info("=== ЗАПУСК БОТА ===")

    db = DB()
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Регистрируем обработчики
    register_handlers(dp)
    
    # Логируем зарегистрированные обработчики
    logger.info("Зарегистрированные обработчики:")
    for handler in dp.message_handlers.handlers:
        logger.info(f"Message handler: {handler}")
    for handler in dp.callback_query_handlers.handlers:
        logger.info(f"Callback handler: {handler}")

    # Запуск фоновой задачи
    asyncio.create_task(passive_income_loop(db))

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
