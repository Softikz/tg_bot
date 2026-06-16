import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, load_data, save_data
from keyboards import set_bot_commands

from handlers_start import router as start_router
from handlers_farm import router as farm_router
from handlers_city import router as city_router
from handlers_deliveries import router as deliveries_router
from handlers_profile import router as profile_router
from handlers_library import router as library_router
from handlers_friends import router as friends_router
from handlers_janna import router as janna_router
from handlers_mine import router as mine_router
from handlers_fishing import router as fishing_router
from handlers_coop import router as coop_router
from handlers_weekly import router as weekly_router, weekly_reward_task
from handlers_festival import router as festival_router
from handlers_shop import router as shop_router
from handlers_flowerbed import router as flowerbed_router
from handlers_commands import router as commands_router

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Сохраняем бота в config для использования в других модулях
import config
config.bot = bot

# Также устанавливаем бота в handlers_commands для broadcast функции
import handlers_commands
handlers_commands.bot = bot

dp.include_router(commands_router)
dp.include_router(start_router)
dp.include_router(farm_router)
dp.include_router(city_router)
dp.include_router(deliveries_router)
dp.include_router(profile_router)
dp.include_router(library_router)
dp.include_router(friends_router)
dp.include_router(janna_router)
dp.include_router(mine_router)
dp.include_router(fishing_router)
dp.include_router(coop_router)
dp.include_router(weekly_router)
dp.include_router(festival_router)
dp.include_router(shop_router)
dp.include_router(flowerbed_router)


async def periodic_save():
    while True:
        await asyncio.sleep(60)
        save_data()


async def main():
    load_data()
    
    # Устанавливаем команды бота с повторными попытками
    try:
        await set_bot_commands(bot, max_retries=3, initial_delay=1.0)
    except Exception as e:
        print(f"⚠️ Ошибка при установке команд: {e}")

    asyncio.create_task(periodic_save())
    asyncio.create_task(weekly_reward_task())

    from config import users
    print("=" * 50)
    print("🌾 Бот Farm Empire полностью запущен!")
    print(f"📊 Пользователей в базе: {len(users)}")
    print("=" * 50)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка во время работы: {e}")
    finally:
        # Аккуратное завершение работы
        print("\n🛑 Запускаю процедуру корректного завершения...")
        
        try:
            # Сохраняем данные пользователей
            save_data()
            print(f"💾 Сохранено пользователей: {len(users)}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении данных: {e}")
        
        try:
            # Завершаем dispatcher
            await dp.fsm.storage.close() if hasattr(dp.fsm, 'storage') else None
            await dp.storage.close() if hasattr(dp, 'storage') else None
        except Exception as e:
            pass  # Может быть ошибка если storage не поддерживает close
        
        try:
            # Закрываем сессию бота (aiohttp)
            await bot.session.close()
            print("✅ Сессия бота закрыта")
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии сессии: {e}")
        
        print("✅ Бот корректно выключен")


if __name__ == "__main__":
    asyncio.run(main())