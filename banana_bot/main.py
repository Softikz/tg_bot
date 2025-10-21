# banana_bot/main.py
import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher, types   # <- как ты просил: импорт с types
from handlers.commands import router
from storage.db import DB
from game.logic import apply_offline_gain

API_TOKEN = "8226054487:AAEiJz0n9FgOpSk62QXpgHWGGFdGjxsy9es"  # замени токен если нужно

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def passive_income_loop(db: DB, interval: int = 1):
    """
    Фоновая задача: обходит всех пользователей в БД,
    считает оффлайновый доход с помощью game.logic.apply_offline_gain
    и сохраняет результат в БД.
    """
    logger.info("🟢 Passive income loop started")
    try:
        while True:
            try:
                rows = db.all_users()
                # rows — список dict'ов (см. storage/db.py)
                for user in rows:
                    added, new_last = apply_offline_gain(user)  # возвращает (added, now)
                    if added:
                        new_bananas = user.get("bananas", 0) + added
                        db.update_user(user["user_id"], bananas=new_bananas, last_update=new_last)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.exception("Error in passive_income_loop iteration: %s", e)
                # в случае ошибки подождём немного, чтобы не спамить
                await asyncio.sleep(5)
    finally:
        logger.info("🔴 Passive income loop stopped")


async def main():
    logger.info("🚀 Бот запускается...")

    # — создаём подключение к БД (sqlite)
    db = DB()

    # — создаём объекты aiogram
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # 🔥 ВАЖНО: подключаем router точно один раз
    dp.include_router(router)

    # — запускаем фоновую задачу (passive income)
    passive_task = asyncio.create_task(passive_income_loop(db))

    # graceful shutdown support
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("SIG received — shutting down...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _signal_handler)
        except NotImplementedError:
            # Windows или окружения без реализации add_signal_handler
            pass

    # Запускаем polling в фоне
    polling_task = asyncio.create_task(dp.start_polling(bot))

    # Ждём сигнала остановки
    await stop_event.wait()
    logger.info("Shutdown initiated")

    # Останавливаем polling и фоновые задачи
    try:
        await dp.stop_polling()
    except Exception as e:
        logger.exception("Error stopping polling: %s", e)

    # отменяем/остановим фоновую задачу аккуратно
    try:
        passive_task.cancel()
        await asyncio.shield(passive_task)
    except asyncio.CancelledError:
        logger.info("Passive income task cancelled")
    except Exception:
        logger.exception("Error while cancelling passive task")

    # закрываем сессии/соединения
    try:
        await bot.session.close()
    except Exception:
        pass

    try:
        db.close()
    except Exception:
        pass

    # убедимся что polling задача завершилась
    try:
        await asyncio.shield(polling_task)
    except Exception:
        pass

    logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
