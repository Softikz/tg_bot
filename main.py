# main.py
import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain

# <-- ВАЖНО: поставь сюда свой токен
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

    db = DB()
    bot = Bot(token=API_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # подключаем роутер (handlers/commands.py импортирует router)
    dp.include_router(router)

    # запуск фоновой задачи
    asyncio.create_task(passive_income_loop(db))

    # обработка сигналов для корректной остановки
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
