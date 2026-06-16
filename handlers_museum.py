from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user

router = Router()

MUSEUM_CATEGORIES = {
    "🥕 Овощи": {
        "items": ["🥕 Морковь", "🧅 Лук", "🥔 Картофель", "🥦 Капуста", "🎃 Тыква", "🍆 Баклажан", "🍠 Батат"],
        "gold_reward": "🪵 1 древесина",
        "reward_type": "wood"
    },
    "🌾 Зерновые": {
        "items": ["🌾 Пшеница", "🌽 Кукуруза", "🍚 Рис"],
        "gold_reward": "🪨 10 камня",
        "reward_type": "stone"
    },
    "🍓 Ягоды": {
        "items": ["🍓 Клубника", "🍇 Виноград"],
        "gold_reward": "🔗 2 железа",
        "reward_type": "iron"
    },
    "🍎 Фрукты": {
        "items": ["🍋 Лимон", "🍒 Вишня", "🍎 Яблоко", "🍌 Банан"],
        "gold_reward": "🌸 Цветок",
        "reward_type": "flower"
    },
    "🥚 Животноводство": {
        "items": ["🥚 Яйца", "🧶 Шерсть", "🥛 Молоко", "🍄 Грибы"],
        "gold_reward": "📄 1 чертеж",
        "reward_type": "blueprint"
    },
    "🐟 Рыба": {
        "items": ["🐡 Фугу", "🦐 Креветка", "🐟 Карась", "🐠 Окунь", "🦈 Щука", "🐋 Белуга"],
        "gold_reward": "🧰 1 сундук с экипировкой [E]",
        "reward_type": "chest"
    }
}

def get_museum_data(user_id: int):
    user = get_user(user_id)
    if "museum" not in user:
        user["museum"] = {}
        for cat, data in MUSEUM_CATEGORIES.items():
            user["museum"][cat] = {}
            for item in data["items"]:
                user["museum"][cat][item] = {"bronze": False, "silver": False, "gold": False}
    return user["museum"]

def count_museum_stats(museum_data: dict):
    bronze = 0
    silver = 0
    gold = 0
    completed = 0
    total = 0
    for cat, items in museum_data.items():
        for item, status in items.items():
            total += 1
            if status["gold"]:
                gold += 1
                completed += 1
            elif status["silver"]:
                silver += 1
            elif status["bronze"]:
                bronze += 1
    return bronze, silver, gold, completed, total

def museum_main_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥕 Овощи", callback_data="museum_cat_🥕 Овощи")],
        [InlineKeyboardButton(text="🌾 Зерновые", callback_data="museum_cat_🌾 Зерновые")],
        [InlineKeyboardButton(text="🍓 Ягоды", callback_data="museum_cat_🍓 Ягоды")],
        [InlineKeyboardButton(text="🍎 Фрукты", callback_data="museum_cat_🍎 Фрукты")],
        [InlineKeyboardButton(text="🥚 Животноводство", callback_data="museum_cat_🥚 Животноводство")],
        [InlineKeyboardButton(text="🐟 Рыба", callback_data="museum_cat_🐟 Рыба")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="museum_stats")],
        [InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")]
    ])
    return kb

def museum_category_kb(category: str, museum_data: dict):
    buttons = []
    items = MUSEUM_CATEGORIES[category]["items"]
    for item in items:
        status = museum_data[category][item]
        if status["gold"]:
            prefix = "🥇"
        elif status["silver"]:
            prefix = "🥈"
        elif status["bronze"]:
            prefix = "🥉"
        else:
            prefix = "⭕"
        buttons.append([InlineKeyboardButton(text=f"{prefix} {item}", callback_data=f"museum_item_{category}_{item}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="museum")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def museum_item_kb(category: str, item: str, museum_data: dict, user: dict):
    status = museum_data[category][item]
    buttons = []
    required = {"bronze": 1, "silver": 10, "gold": 100}
    item_clean = item.split(" ", 1)[1] if " " in item else item
    for tier, amount in required.items():
        if not status[tier]:
            have = user["harvest"].get(item_clean, 0)
            if have >= amount:
                buttons.append([InlineKeyboardButton(text=f"🥉 Сдать {tier} ({amount} шт.)", callback_data=f"museum_donate_{category}_{item}_{tier}")])
            else:
                buttons.append([InlineKeyboardButton(text=f"❌ Не хватает ({have}/{amount})", callback_data="no_res")])
            break
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к категории", callback_data=f"museum_cat_{category}")])
    buttons.append([InlineKeyboardButton(text="⬅️ К категориям музея", callback_data="museum")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data == "museum")
async def museum_main(call: types.CallbackQuery):
    museum_data = get_museum_data(call.from_user.id)
    bronze, silver, gold, completed, total = count_museum_stats(museum_data)
    percent = round(completed / total * 100) if total > 0 else 0
    text = (
        "🏛️ Музей фермера\n\n"
        "Добро пожаловать в музей! Здесь вы можете сдавать выращенные растения и продукты животных получая за это ценные награды.\n\n"
        f"📊 Ваш прогресс:\n"
        f"🥉 Бронзовых наград: {bronze}\n"
        f"🥈 Серебряных наград: {silver}\n"
        f"🥇 Золотых наград: {gold}\n"
        f"✅ Завершено: {completed}/{total} ({percent}%)\n\n"
        "💡 Как это работает:\n"
        "• Выберите категорию экспонатов\n"
        "• Выберите продукт для сдачи\n"
        "• Сдайте 1, 10 и 100 единиц последовательно\n"
        "• Получайте награды: 500💰, 5,000💰 и 50,000💰\n"
        "• За золото также получаете особый ресурс:\n"
        "  🥕 Овощи → 🪵 древесина\n"
        "  🌾 Зерновые → 🪨 камень\n"
        "  🍓 Ягоды → 🔗 железо\n"
        "  🍎 Фрукты → 🌸 цветок\n"
        "  🥚 Животноводство → 📄 чертеж\n"
        "  🐟 Рыба → 🧰 сундук с экипировкой [E]\n\n"
        "🎁 Награда за 100%: стикеры \"Коровушка (часть 2)\"\n\n"
        "Выберите категорию:"
    )
    await call.message.edit_text(text, reply_markup=museum_main_kb())

@router.callback_query(F.data.startswith("museum_cat_"))
async def museum_category(call: types.CallbackQuery):
    category = call.data.replace("museum_cat_", "")
    museum_data = get_museum_data(call.from_user.id)
    items = MUSEUM_CATEGORIES[category]["items"]
    completed = sum(1 for item in items if museum_data[category][item]["gold"])
    gold_reward = MUSEUM_CATEGORIES[category]["gold_reward"]
    legend = "⭕ - Не начато\n🥉 - Бронза\n🥈 - Серебро\n🥇 - Золото (завершено)"
    text = (
        f"🏛️ Музей фермера | {category}\n\n"
        f"📊 Прогресс: {completed}/{len(items)} завершено\n"
        f"🥇 Золотая награда: {gold_reward}\n\n"
        "Выберите экспонат для просмотра деталей:\n\n"
        f"Легенда:\n{legend}\n"
    )
    for item in items:
        status = museum_data[category][item]
        if status["gold"]:
            prefix = "🥇"
        elif status["silver"]:
            prefix = "🥈"
        elif status["bronze"]:
            prefix = "🥉"
        else:
            prefix = "⭕"
        text += f"\n{prefix} {item}"
    await call.message.edit_text(text, reply_markup=museum_category_kb(category, museum_data))

@router.callback_query(F.data.startswith("museum_item_"))
async def museum_item(call: types.CallbackQuery):
    parts = call.data.replace("museum_item_", "").split("_", 1)
    category = parts[0]
    item = parts[1] if len(parts) > 1 else ""
    museum_data = get_museum_data(call.from_user.id)
    user = get_user(call.from_user.id)
    status = museum_data[category][item]
    item_clean = item.split(" ", 1)[1] if " " in item else item
    text = f"🏛️ Музей | {item}\n\n📊 Ваш прогресс:\n\n"
    rewards = {"bronze": "500💰", "silver": "5,000💰", "gold": f"50,000💰 + {MUSEUM_CATEGORIES[category]['gold_reward']}"}
    for tier in ["bronze", "silver", "gold"]:
        check = "✅" if status[tier] else "❌"
        amount = {"bronze": 1, "silver": 10, "gold": 100}[tier]
        text += f"🥉 {tier.capitalize()} ({amount} шт.) - {check} {rewards[tier]}\n"
    if status["gold"]:
        text += "\n🎉 Поздравляем! Вы полностью завершили этот экспонат!"
    await call.message.edit_text(text, reply_markup=museum_item_kb(category, item, museum_data, user))

@router.callback_query(F.data.startswith("museum_donate_"))
async def museum_donate(call: types.CallbackQuery):
    parts = call.data.replace("museum_donate_", "").split("_")
    category = parts[0]
    item = "_".join(parts[1:-1])
    tier = parts[-1]
    user = get_user(call.from_user.id)
    museum_data = get_museum_data(call.from_user.id)
    item_clean = item.split(" ", 1)[1] if " " in item else item
    amounts = {"bronze": 1, "silver": 10, "gold": 100}
    rewards_money = {"bronze": 500, "silver": 5000, "gold": 50000}
    required = amounts[tier]
    have = user["harvest"].get(item_clean, 0)
    if have < required:
        await call.answer("Недостаточно ресурсов!")
        return
    user["harvest"][item_clean] -= required
    user["money"] += rewards_money[tier]
    museum_data[category][item][tier] = True
    if tier == "gold":
        reward_type = MUSEUM_CATEGORIES[category]["reward_type"]
        if reward_type == "wood":
            user["harvest"]["🪵 древесина"] = user["harvest"].get("🪵 древесина", 0) + 1
        elif reward_type == "stone":
            user["harvest"]["🪨 камень"] = user["harvest"].get("🪨 камень", 0) + 10
        elif reward_type == "iron":
            user["harvest"]["🔗 железо"] = user["harvest"].get("🔗 железо", 0) + 2
        elif reward_type == "flower":
            user["harvest"]["🌸 цветок"] = user["harvest"].get("🌸 цветок", 0) + 1
        elif reward_type == "blueprint":
            user["harvest"]["📄 чертеж"] = user["harvest"].get("📄 чертеж", 0) + 1
        elif reward_type == "chest":
            user["harvest"]["🧰 сундук"] = user["harvest"].get("🧰 сундук", 0) + 1
    await call.answer(f"Сдано! +{rewards_money[tier]}💰")
    # Обновить страницу
    await museum_item(call)

@router.callback_query(F.data == "museum_stats")
async def museum_stats(call: types.CallbackQuery):
    museum_data = get_museum_data(call.from_user.id)
    user = get_user(call.from_user.id)
    bronze, silver, gold, completed, total = count_museum_stats(museum_data)
    percent = round(completed / total * 100) if total > 0 else 0
    total_money = bronze * 500 + silver * 5000 + gold * 50000
    text = (
        "🏛️ Статистика музея\n\n"
        f"📊 Общий прогресс:\n"
        f"🥉 Бронзовых наград: {bronze}/{total}\n"
        f"🥈 Серебряных наград: {silver}/{total}\n"
        f"🥇 Золотых наград: {gold}/{total}\n\n"
        f"✅ Завершено экспонатов: {completed}/{total}\n"
        f"📈 Процент завершения: {percent}%\n\n"
        "📁 По категориям:\n"
    )
    for cat, data in MUSEUM_CATEGORIES.items():
        completed_cat = sum(1 for item in data["items"] if museum_data[cat][item]["gold"])
        text += f"{cat}: {completed_cat}/{len(data['items'])}\n"
    text += f"\n💰 Всего заработано монет: {total_money:,}💰"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к музею", callback_data="museum")],
        [InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")]
    ])
    await call.message.edit_text(text, reply_markup=kb)