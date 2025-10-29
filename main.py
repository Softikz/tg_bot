# main.py
import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain

API_TOKEN = "ВАШ_ТОКЕН_ТУТ"  # вставь свой токен бота

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def passive_income_loop(db: DB, interval: int = 1):
    """Фоновая задача — начисление пассивного дохода."""
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

    db = DB()
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(router)

    # Фоновая задача пассивного дохода
    asyncio.create_task(passive_income_loop(db))

    # --- Обработка сигналов ---
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("SIG received — shutting down...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _signal_handler)
        except NotImplementedError:
            pass

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
