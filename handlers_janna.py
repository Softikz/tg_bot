import random
from datetime import datetime
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user

router = Router()

WHEEL_SYMBOLS = ["BAR", "🍒", "🍋", "7️⃣"]

DAILY_TASKS = [
    {
        "id": "task_harvest_3",
        "name": "🌱 Собери 3 урожая",
        "description": "Собери урожай с грядок 3 раза",
        "target": 3,
        "task_type": "harvest",
        "reward": {"tickets": 1, "exp": 30, "money": 200}
    },
    {
        "id": "task_plant_5",
        "name": "🌾 Посади 5 культур",
        "description": "Посади любые семена на грядки 5 раз",
        "target": 5,
        "task_type": "plant_variety",
        "reward": {"tickets": 1, "exp": 50, "money": 300}
    },
    {
        "id": "task_sell_10",
        "name": "💰 Продай 10 овощей",
        "description": "Продай любые овощи на Овощебазе",
        "target": 10,
        "task_type": "sell",
        "reward": {"tickets": 2, "exp": 80, "money": 500}
    },
    {
        "id": "task_visit_3",
        "name": "👥 Посети 3 фермы",
        "description": "Посети фермы 3 разных соседей",
        "target": 3,
        "task_type": "visit",
        "reward": {"tickets": 1, "exp": 40, "money": 250}
    },
    {
        "id": "task_clear_2",
        "name": "🧹 Расчисти 2 грядки",
        "description": "Расчисти заросшие грядки",
        "target": 2,
        "task_type": "clear",
        "reward": {"tickets": 1, "exp": 35, "money": 200}
    },
    {
        "id": "task_earn_500",
        "name": "💵 Заработай 500 монет",
        "description": "Заработай 500 монет продажей",
        "target": 500,
        "task_type": "earn",
        "reward": {"tickets": 2, "exp": 100, "money": 400}
    },
]


def get_wheel_reward(combo):
    s1, s2, s3 = combo
    if s1 == s2 == s3:
        if s1 == "BAR":

            # Возвращаем ключи семян в виде emoji, чтобы хранение и посадка были согласованы
            return {"type": "seeds", "item": "🌼", "amount": 1}
        elif s1 == "🍒":
            return {"type": "seeds", "item": "🍒", "amount": 5}
        elif s1 == "🍋":
            return {"type": "seeds", "item": "🍋", "amount": 5}
        elif s1 == "7️⃣":
            return {"type": "resource", "item": "🪵 древесина", "amount": 1}

    if combo.count("7️⃣") == 2:
        return {"type": "tool", "item": "⛏️ Тяпка", "amount": 1}
    if combo.count("BAR") == 2:
        return {"type": "bait", "item": "🪱 Червяк", "amount": 1}
    if combo.count("🍒") == 2:
        return {"type": "seeds", "item": "🍒", "amount": 3}
    if combo.count("🍋") == 2:
        return {"type": "seeds", "item": "🍋", "amount": 3}
    if s1 == "7️⃣" and s3 == "7️⃣":
        return {"type": "fertilizer", "item": "💩 Удобрение", "amount": 1}
    if "7️⃣" in combo:
        return {"type": "stars", "item": "⭐ Звезды", "amount": combo.count("7️⃣") * 2}
    return {"type": "stars", "item": "⭐ Звезды", "amount": 1}


def get_daily_tasks(user_id: int):
    user = get_user(user_id)
    if "daily_tasks" not in user:
        user["daily_tasks"] = {}

    today = datetime.now().strftime("%Y-%m-%d")
    if user["daily_tasks"].get("date") != today:
        tasks = random.sample(DAILY_TASKS, min(3, len(DAILY_TASKS)))
        user["daily_tasks"] = {
            "date": today,
            "current": {},
            "claimed": {}
        }
        for t in tasks:
            user["daily_tasks"]["current"][t["id"]] = 0

    return user["daily_tasks"]


def update_daily_task_progress(user_id: int, task_type: str, amount: int = 1):
    """Обновляет прогресс ежедневных заданий Доярки Жанны"""
    user = get_user(user_id)
    tasks = get_daily_tasks(user_id)

    if "current" not in tasks:
        return

    for task_id, progress in tasks["current"].items():
        task_info = next((t for t in DAILY_TASKS if t["id"] == task_id), None)
        if task_info and task_info["task_type"] == task_type:
            if task_id not in tasks["claimed"]:
                tasks["current"][task_id] = progress + amount


@router.callback_query(F.data == "janna")
async def janna_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    tasks = get_daily_tasks(call.from_user.id)

    today = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_free_ticket") != today:
        user["last_free_ticket"] = today
        user["luck_tickets"] = user.get("luck_tickets", 0) + 1
        free_ticket_msg = "\n🎫 Получен ежедневный бесплатный билет!"
    else:
        free_ticket_msg = ""

    text = "👩‍🌾 Доярка Жанна\n\n"
    text += "Привет, фермер! У меня есть ежедневные задания и Колесо удачи!\n\n"
    text += "📋 Ежедневные задания:\n"

    if "current" in tasks:
        for task_id, progress in tasks["current"].items():
            task_info = next((t for t in DAILY_TASKS if t["id"] == task_id), None)
            if task_info:
                if task_id in tasks.get("claimed", {}):
                    done = "✅"
                elif progress >= task_info["target"]:
                    done = "🎁"
                else:
                    done = f"🔄 {progress}/{task_info['target']}"
                text += f"{done} {task_info['name']} — 🎫+{task_info['reward']['tickets']}\n"

    text += f"\n🎫 Билетов удачи: {user.get('luck_tickets', 0)}{free_ticket_msg}"
    text += "\n🎰 Колесо удачи: 1 попытка = 1 🎫 билет"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить колесо (1🎫)", callback_data="spin_wheel")],
        [InlineKeyboardButton(text="🎰 Крутить 3 раза (3🎫)", callback_data="spin_wheel_3")],
        [InlineKeyboardButton(text="🎰 Крутить 5 раз (5🎫)", callback_data="spin_wheel_5")],
        [InlineKeyboardButton(text="📋 Проверить задания", callback_data="check_daily_tasks")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "check_daily_tasks")
async def check_daily_tasks(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    tasks = get_daily_tasks(call.from_user.id)

    text = "👩‍🌾 Доярка Жанна — Ежедневные задания\n\n"
    text += "⏰ Задания обновляются каждый день в 6:00\n"
    text += "✅ Выполняйте задания и получайте 🎫 билеты удачи!\n\n"

    completed_count = 0
    if "current" in tasks:
        for task_id, progress in tasks["current"].items():
            task_info = next((t for t in DAILY_TASKS if t["id"] == task_id), None)
            if task_info:
                if task_id in tasks.get("claimed", {}):
                    text += f"✅ {task_info['name']} — ВЫПОЛНЕНО!\n\n"
                    completed_count += 1
                elif progress >= task_info["target"]:
                    # Выдаём награду
                    tasks["claimed"][task_id] = True
                    user["luck_tickets"] = user.get("luck_tickets", 0) + task_info["reward"]["tickets"]
                    user["exp"] = user.get("exp", 0) + task_info["reward"]["exp"]
                    user["money"] = user.get("money", 0) + task_info["reward"]["money"]
                    text += f"🎁 {task_info['name']} — ВЫПОЛНЕНО!\n"
                    text += f"   Награда: 🎫+{task_info['reward']['tickets']}, +{task_info['reward']['exp']} опыта, +{task_info['reward']['money']}💰\n\n"
                    completed_count += 1
                else:
                    text += f"🔄 {task_info['name']}\n"
                    text += f"   Прогресс: {progress}/{task_info['target']}\n\n"

    if completed_count > 0:
        text += f"🎉 Выполнено заданий: {completed_count}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К Доярке Жанне", callback_data="janna")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("spin_wheel"))
async def spin_wheel_handler(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if call.data == "spin_wheel":
        spins = 1
    elif call.data == "spin_wheel_3":
        spins = 3
    elif call.data == "spin_wheel_5":
        spins = 5
    else:
        spins = 1

    if user.get("luck_tickets", 0) < spins:
        await call.answer(f"❌ Недостаточно билетов! Нужно {spins}🎫, у вас {user.get('luck_tickets', 0)}🎫")
        return

    user["luck_tickets"] -= spins
    results = []

    for _ in range(spins):
        combo = (random.choice(WHEEL_SYMBOLS), random.choice(WHEEL_SYMBOLS), random.choice(WHEEL_SYMBOLS))
        reward = get_wheel_reward(combo)
        results.append((combo, reward))

        if reward["type"] == "stars":
            user["stars"] = user.get("stars", 0) + reward["amount"]
        elif reward["type"] == "seeds":
            # reward['item'] должен быть emoji (например '🍋')
            seed_key = reward.get("item")
            if seed_key:
                user["seeds"][seed_key] = user["seeds"].get(seed_key, 0) + reward["amount"]
        elif reward["type"] == "tool":
            user["harvest"]["⛏️ Тяпка"] = user["harvest"].get("⛏️ Тяпка", 0) + reward["amount"]
        elif reward["type"] == "resource":
            user["harvest"][reward["item"]] = user["harvest"].get(reward["item"], 0) + reward["amount"]
        elif reward["type"] == "fertilizer":
            user["harvest"]["💩 Удобрение"] = user["harvest"].get("💩 Удобрение", 0) + reward["amount"]
        elif reward["type"] == "bait":
            user["harvest"]["🪱 Червяк"] = user["harvest"].get("🪱 Червяк", 0) + reward["amount"]

    if spins == 1:
        combo, reward = results[0]
        text = (
            f"🎰 Колесо удачи!\n\n"
            f"🎲 Комбинация: {' '.join(combo)}\n\n"
            f"🎁 Награда: {reward['item']} x{reward['amount']}\n\n"
            f"🎫 Осталось билетов: {user.get('luck_tickets', 0)}"
        )
    else:
        text = f"🎰 Колесо удачи — {spins} попытки!\n\n"
        for i, (combo, reward) in enumerate(results, 1):
            text += f"{i}. {' '.join(combo)} → {reward['item']} x{reward['amount']}\n"
        text += f"\n🎫 Осталось билетов: {user.get('luck_tickets', 0)}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить ещё (1🎫)", callback_data="spin_wheel")],
        [InlineKeyboardButton(text="🎰 Крутить 3 раза (3🎫)", callback_data="spin_wheel_3")],
        [InlineKeyboardButton(text="⬅️ К Доярке Жанне", callback_data="janna")],
    ])
    await call.message.edit_text(text, reply_markup=kb)