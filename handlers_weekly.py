import asyncio
from datetime import datetime, time, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, users
from aiogram import Bot

router = Router()

WEEKLY_REWARDS = {
    1: {"money": 100000, "stars": 50, "silage": 10, "feed": 5, "tickets": 10, "fertilizer": 5},
    2: {"money": 75000, "stars": 30, "silage": 7, "feed": 3, "tickets": 7, "fertilizer": 3},
    3: {"money": 50000, "stars": 20, "silage": 5, "feed": 2, "tickets": 5, "fertilizer": 2},
}


def get_top_players():
    sorted_users = sorted(
        [(uid, data) for uid, data in users.items() if data.get("name")],
        key=lambda x: (x[1].get("level", 1), x[1].get("exp", 0)),
        reverse=True
    )
    return sorted_users


async def weekly_reward_task():
    while True:
        now = datetime.now()
        target = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if now.weekday() != 6:
            days_until_sunday = 6 - now.weekday()
            target = target + timedelta(days=days_until_sunday)
        if now > target:
            target = target + timedelta(days=7)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        top = get_top_players()[:3]
        for rank, (uid, data) in enumerate(top, 1):
            if rank in WEEKLY_REWARDS:
                reward = WEEKLY_REWARDS[rank]
                user = get_user(uid)
                user["money"] += reward["money"]
                user["stars"] += reward["stars"]
                user["harvest"]["🌿 Силос"] = user["harvest"].get("🌿 Силос", 0) + reward["silage"]
                user["harvest"]["🥜 Комбикорм"] = user["harvest"].get("🥜 Комбикорм", 0) + reward["feed"]
                user["luck_tickets"] += reward["tickets"]
                user["harvest"]["💩 Удобрение"] = user["harvest"].get("💩 Удобрение", 0) + reward["fertilizer"]

                try:
                    await bot.send_message(
                        uid,
                        f"🏆 Еженедельная награда рейтинга!\n\n"
                        f"Ваше место: {rank}\n"
                        f"🎁 Награда:\n"
                        f"💰 {reward['money']} монет\n"
                        f"⭐ {reward['stars']} звёзд\n"
                        f"🌿 {reward['silage']} силоса\n"
                        f"🥜 {reward['feed']} комбикорма\n"
                        f"🎫 {reward['tickets']} билетов удачи\n"
                        f"💩 {reward['fertilizer']} удобрений\n\n"
                        f"Поздравляем!",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="ratings")],
                        ])
                    )
                except:
                    pass

# Запускается при старте бота