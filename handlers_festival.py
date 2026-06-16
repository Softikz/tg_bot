import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, bot, users

router = Router()

FESTIVAL_CONFIGS = [
    {
        "name": "Праздник урожая",
        "emoji": "🎪",
        "target_items": ["🥕 Морковь", "🧅 Лук", "🥔 Картофель"],
        "points_per_item": 10,
        "duration_days": 3,
        "rewards": {
            100: {"money": 5000, "exp": 200, "tickets": 5},
            300: {"money": 15000, "exp": 500, "tickets": 10, "seeds": {"🍓": 10}},
            500: {"money": 30000, "exp": 1000, "tickets": 20, "seeds": {"🍇": 10}, "stars": 10},
            1000: {"money": 100000, "exp": 3000, "tickets": 50, "stars": 30, "blueprint": 1},
        }
    },
    {
        "name": "Молочная лихорадка",
        "emoji": "🥛",
        "target_items": ["🥛 Молоко", "🧀 Сыр", "🧈 Масло (из молока)"],
        "points_per_item": 25,
        "duration_days": 3,
        "rewards": {
            200: {"money": 8000, "exp": 300, "tickets": 7},
            500: {"money": 20000, "exp": 700, "stars": 5},
            1000: {"money": 50000, "exp": 1500, "stars": 20, "wood": 3},
            2000: {"money": 150000, "exp": 5000, "stars": 50, "blueprint": 3},
        }
    },
    {
        "name": "Рыбный день",
        "emoji": "🐟",
        "target_items": ["🐟 Карась", "🐠 Окунь", "🦈 Щука"],
        "points_per_item": 30,
        "duration_days": 3,
        "rewards": {
            150: {"money": 10000, "exp": 400},
            400: {"money": 25000, "exp": 800, "tickets": 10},
            800: {"money": 60000, "exp": 2000, "stars": 15, "iron": 5},
            1500: {"money": 200000, "exp": 6000, "stars": 40, "blueprint": 2},
        }
    },
]

# Глобальное хранилище фестивалей
festivals = {}

def get_active_festival():
    if "active_festival" not in festivals:
        config = random.choice(FESTIVAL_CONFIGS)
        festivals["active_festival"] = {
            "config": config,
            "started_at": datetime.now(),
            "ends_at": datetime.now() + timedelta(days=config["duration_days"]),
            "participants": {},
        }
    elif datetime.now() > festivals["active_festival"]["ends_at"]:
        config = random.choice(FESTIVAL_CONFIGS)
        festivals["active_festival"] = {
            "config": config,
            "started_at": datetime.now(),
            "ends_at": datetime.now() + timedelta(days=config["duration_days"]),
            "participants": {},
        }
    return festivals["active_festival"]

def get_user_festival_points(user_id: int):
    festival = get_active_festival()
    return festival["participants"].get(str(user_id), 0)

@router.callback_query(F.data == "festival")
async def festival_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("level", 1) < 3:
        await call.answer("🎪 Фестивали доступны с 3 уровня!")
        return

    festival = get_active_festival()
    config = festival["config"]
    points = get_user_festival_points(call.from_user.id)
    remaining = festival["ends_at"] - datetime.now()
    hours = max(0, int(remaining.total_seconds() // 3600))
    mins = max(0, int((remaining.total_seconds() % 3600) // 60))

    text = (
        f"{config['emoji']} Фестиваль «{config['name']}»\n\n"
        f"⏰ Осталось: {hours}ч {mins}м\n"
        f"🎯 Ваши очки: {points}\n\n"
        "📋 Принимаемые товары:\n"
    )
    for item in config["target_items"]:
        have = user["harvest"].get(item, 0)
        text += f"• {item} (+{config['points_per_item']} очков) — у вас: {have}\n"

    text += "\n🏆 Награды:\n"
    for threshold, reward in sorted(config["rewards"].items()):
        done = "✅" if points >= threshold else "⬜"
        text += f"{done} {threshold} очков: "
        parts = []
        if "money" in reward: parts.append(f"{reward['money']}💰")
        if "exp" in reward: parts.append(f"+{reward['exp']} опыта")
        if "tickets" in reward: parts.append(f"{reward['tickets']}🎫")
        if "stars" in reward: parts.append(f"{reward['stars']}⭐")
        if "blueprint" in reward: parts.append(f"{reward['blueprint']}📄")
        if "wood" in reward: parts.append(f"{reward['wood']}🪵")
        if "iron" in reward: parts.append(f"{reward['iron']}🔗")
        text += ", ".join(parts) + "\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Сдать товары", callback_data="festival_donate")],
        [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="festival_leaderboard")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "festival_donate")
async def festival_donate(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    festival = get_active_festival()
    config = festival["config"]

    buttons = []
    for item in config["target_items"]:
        have = user["harvest"].get(item, 0)
        if have > 0:
            buttons.append([InlineKeyboardButton(
                text=f"{item} (у вас: {have}) — Сдать 1 (+{config['points_per_item']} очков)",
                callback_data=f"fest_donate_{item}_1"
            )])
            if have >= 10:
                buttons.append([InlineKeyboardButton(
                    text=f"{item} — Сдать 10 (+{config['points_per_item']*10} очков)",
                    callback_data=f"fest_donate_{item}_10"
                )])

    if not buttons:
        await call.answer("Нет подходящих товаров для сдачи!")
        return

    buttons.append([InlineKeyboardButton(text="⬅️ К фестивалю", callback_data="festival")])
    await call.message.edit_text(
        "📦 Сдача товаров на фестиваль\n\nВыберите товар и количество:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("fest_donate_"))
async def festival_donate_item(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    festival = get_active_festival()
    config = festival["config"]
    parts = call.data.replace("fest_donate_", "").split("_")
    item = "_".join(parts[:-1])
    amount = int(parts[-1])

    have = user["harvest"].get(item, 0)
    if have < amount:
        await call.answer("Недостаточно товара!")
        return

    user["harvest"][item] -= amount
    points = config["points_per_item"] * amount
    festival["participants"][str(call.from_user.id)] = get_user_festival_points(call.from_user.id) + points

    total_points = festival["participants"][str(call.from_user.id)]
    rewards_claimed = []
    for threshold, reward in sorted(config["rewards"].items()):
        if total_points >= threshold:
            claim_key = f"fest_claimed_{config['name']}_{threshold}"
            if not user.get(claim_key):
                user[claim_key] = True
                rewards_claimed.append((threshold, reward))

    for threshold, reward in rewards_claimed:
        if "money" in reward: user["money"] = user.get("money", 0) + reward["money"]
        if "exp" in reward: user["exp"] = user.get("exp", 0) + reward["exp"]
        if "tickets" in reward: user["luck_tickets"] = user.get("luck_tickets", 0) + reward["tickets"]
        if "stars" in reward: user["stars"] = user.get("stars", 0) + reward["stars"]
        if "blueprint" in reward: user["harvest"]["📄 чертеж"] = user["harvest"].get("📄 чертеж", 0) + reward["blueprint"]
        if "seeds" in reward:
            for seed, amt in reward["seeds"].items():
                user["seeds"][seed] = user["seeds"].get(seed, 0) + amt
        if "wood" in reward: user["harvest"]["🪵 древесина"] = user["harvest"].get("🪵 древесина", 0) + reward["wood"]
        if "iron" in reward: user["harvest"]["🔗 железо"] = user["harvest"].get("🔗 железо", 0) + reward["iron"]

    text = f"📦 Сдано {item} x{amount} — +{points} очков!\n"
    text += f"Всего очков: {total_points}\n"
    if rewards_claimed:
        text += "\n🎁 Получены награды!\n"
        for threshold, reward in rewards_claimed:
            text += f"✅ За {threshold} очков\n"

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Сдать ещё", callback_data="festival_donate")],
        [InlineKeyboardButton(text="🎪 К фестивалю", callback_data="festival")],
    ]))

@router.callback_query(F.data == "festival_leaderboard")
async def festival_leaderboard(call: types.CallbackQuery):
    festival = get_active_festival()
    participants = festival["participants"]
    sorted_parts = sorted(participants.items(), key=lambda x: x[1], reverse=True)[:20]

    text = f"🏆 Таблица лидеров — «{festival['config']['name']}»\n\n"
    if sorted_parts:
        for i, (uid, points) in enumerate(sorted_parts, 1):
            name = users[int(uid)]["name"] if int(uid) in users else "Игрок"
            text += f"{i}. {name} — {points} очков\n"
    else:
        text += "Пока нет участников"

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К фестивалю", callback_data="festival")],
    ]))