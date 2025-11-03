# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain

API_TOKEN = "8226054487:AAEiJz0n9FgOpSk62QXpgHWGGFdGjxsy9es"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

bot = None  # глобально, чтобы можно было использовать из других модулей


async def passive_income_loop(db: DB, interval: int = 1):
    """Фоновая задача: начисление пассивного дохода."""
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
    """Фоновая задача: проверка и очистка ивентов."""
    logger.info("🟢 Event checker loop started")
    while True:
        try:
            db.check_and_remove_expired_events()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.exception(f"Error in event_checker_loop: {e}")
            await asyncio.sleep(60)


async def main():
    global bot
    logger.info("🚀 Запуск Telegram-бота...")

    # Инициализация базы данных (данные сохраняются в /data/database.db)
    db = DB()
    logger.info("✅ Database initialized")

    # Инициализация Telegram-бота
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Подключаем обработчики
    dp.include_router(router)
    logger.info("✅ Router connected")

    # Фоновые задачи
    asyncio.create_task(passive_income_loop(db))
    asyncio.create_task(event_checker_loop(db))
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

