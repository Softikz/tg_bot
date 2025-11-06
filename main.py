# main.py
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain, current_time

API_TOKEN = "8226054487:AAEiJz0n9FgOpSk62QXpgHWGGFdGjxsy9es"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

bot = None

async def passive_income_loop(db: DB, interval: int = 1):
    logger.info("🟢 Passive income loop started")
    while True:
        try:
            for user in db.all_users():
                added, new_last = apply_offline_gain(user)
                if added:
                    db.update_user(
                        user["user_id"],
                        bananas=user.get("bananas", 0) + added,
                        last_update=new_last
                    )
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception(f"Error in passive_income_loop: {e}")
            await asyncio.sleep(5)

async def event_checker_loop(db: DB, interval: int = 30):
    logger.info("🟢 Event checker loop started")
    while True:
        try:
            db.check_and_remove_expired_events()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception(f"Error in event_checker_loop: {e}")
            await asyncio.sleep(60)

async def banana_cleaner_loop(db: DB, interval: int = 60):
    """Фоновая задача: очистка просроченных бананов."""
    logger.info("🟢 Banana cleaner loop started")
    while True:
        try:
            current_time_val = current_time()
            users = db.all_users()
            cleaned_count = 0
            
            for user in users:
                # Проверяем, истекло ли время банана
                if user.get("gold_expires", 0) > 0 and user.get("gold_expires", 0) <= current_time_val:
                    try:
                        db.update_user(
                            user["user_id"],
                            active_banana_type="",
                            active_banana_multiplier=1.0
                        )
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Could not clean banana for user {user['user_id']}: {e}")
                        continue
            
            if cleaned_count > 0:
                logger.info(f"🧹 Очищено {cleaned_count} просроченных бананов")
                
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception(f"Error in banana_cleaner_loop: {e}")
            await asyncio.sleep(300)

async def main():
    global bot
    logger.info("🚀 Запуск Telegram-бота...")

    db = DB()
    logger.info("✅ Database initialized")

    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    dp.include_router(router)
    logger.info("✅ Router connected")

    # Фоновые задачи
    asyncio.create_task(passive_income_loop(db))
    asyncio.create_task(event_checker_loop(db))
    # Временно отключаем очистку бананов до исправления базы
    # asyncio.create_task(banana_cleaner_loop(db))
    logger.info("✅ Background tasks started")

    # Запуск long polling
    try:
        logger.info("🔗 Connecting to Telegram...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        db.close()
        logger.info("🔴 Bot stopped, DB closed.")

if __name__ == "__main__":
    asyncio.run(main())
