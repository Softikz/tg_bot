from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user
from datetime import datetime, timedelta

router = Router()

# ID админа
ADMIN_ID = 5748972158

SHOP_ITEMS = {
    "seeds": [
        {"name": "🥕 Семена моркови", "price": 10, "emoji": "🥕"},
        {"name": "🧅 Семена лука", "price": 20, "emoji": "🧅"},
        {"name": "🥔 Семена картофеля", "price": 50, "emoji": "🥔"},
        {"name": "🥦 Семена капусты", "price": 80, "emoji": "🥦"},
        {"name": "🌾 Семена пшеницы", "price": 200, "emoji": "🌾"},
        {"name": "🌽 Семена кукурузы", "price": 300, "emoji": "🌽"},
        {"name": "🍓 Семена клубники", "price": 500, "emoji": "🍓"},
        {"name": "🍇 Семена винограда", "price": 700, "emoji": "🍇"},
    ],
}

PREMIUM_ITEMS = [
    {"name": "🎫 5 билетов удачи", "price": 10, "gives": {"tickets": 5}},
    {"name": "💩 Удобрение x3", "price": 15, "gives": {"fertilizer": 3}},
    {"name": "🌿 Силос x5", "price": 10, "gives": {"silage": 5}},
    {"name": "🥜 Комбикорм x3", "price": 20, "gives": {"feed": 3}},
    {"name": "🪵 Древесина x1", "price": 30, "gives": {"wood": 1}},
    {"name": "🪨 Камень x10", "price": 20, "gives": {"stone": 10}},
    {"name": "🔗 Железо x5", "price": 25, "gives": {"iron": 5}},
    {"name": "📄 Чертеж x1", "price": 50, "gives": {"blueprint": 1}},
    {"name": "⛏️ Тяпка x1", "price": 15, "gives": {"pickaxe": 1}},
    {"name": "🪱 Червяк x3", "price": 10, "gives": {"worms": 3}},
]


@router.callback_query(F.data == "shop")
async def shop_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    text = (
        "🏪 Магазин\n\n"
        f"💰 Монеты: {user.get('money', 0)}\n"
        f"⭐ Звёзды: {user.get('stars', 0)}\n\n"
        "📂 Выберите раздел:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Семена", callback_data="shop_seeds")],
        [InlineKeyboardButton(text="🟫 Грядки", callback_data="shop_beds")],
        [InlineKeyboardButton(text="🔧 Инструменты", callback_data="shop_tools")],
        [InlineKeyboardButton(text="⭐ Премиум магазин", callback_data="shop_premium")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "shop_seeds")
async def shop_seeds(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    text = "🌱 Семена\n\n"
    buttons = []
    for item in SHOP_ITEMS["seeds"]:
        text += f"{item['name']} — 💰{item['price']}\n"
        buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — 💰{item['price']}",
            callback_data=f"buy_seed_{item['emoji']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ В магазин", callback_data="shop")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("buy_seed_"))
async def buy_seed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    seed_emoji = call.data.replace("buy_seed_", "")
    item = next((i for i in SHOP_ITEMS["seeds"] if i["emoji"] == seed_emoji), None)
    if not item:
        return
    if user.get("money", 0) < item["price"]:
        await call.answer(f"❌ Недостаточно монет! Нужно 💰{item['price']}")
        return
    user["money"] -= item["price"]
    user["seeds"][seed_emoji] = user["seeds"].get(seed_emoji, 0) + 10
    await call.answer(f"✅ Куплено {item['name']} x10!")
    await shop_seeds(call)


@router.callback_query(F.data == "shop_beds")
async def shop_beds(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    cost = 5000 + (user["beds"] - 2) * 5000
    text = (
        f"🟫 Грядки\n\n"
        f"У вас грядок: {user['beds']}\n"
        f"Стоимость новой: 💰{cost}\n\n"
        f"Каждая следующая дороже на 💰5000."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🟫 Купить грядку — 💰{cost}", callback_data="buy_bed")],
        [InlineKeyboardButton(text="⬅️ В магазин", callback_data="shop")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "buy_bed")
async def buy_bed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    cost = 5000 + (user["beds"] - 2) * 5000
    if user.get("money", 0) < cost:
        await call.answer(f"❌ Недостаточно монет! Нужно 💰{cost}")
        return
    user["money"] -= cost
    user["beds"] += 1
    user["beds_data"].append({"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None})
    await call.answer(f"✅ Грядка куплена! Всего: {user['beds']}")
    await shop_beds(call)


@router.callback_query(F.data == "shop_tools")
async def shop_tools(call: types.CallbackQuery):
    text = (
        "🔧 Инструменты\n\n"
        "⛏️ Тяпка — 💰1000 (для шахты)\n"
        "🪱 Червяк — 💰500 (для рыбалки)\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏️ Тяпка — 💰1000", callback_data="buy_tool_pickaxe")],
        [InlineKeyboardButton(text="🪱 Червяк — 💰500", callback_data="buy_tool_worm")],
        [InlineKeyboardButton(text="⬅️ В магазин", callback_data="shop")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "buy_tool_pickaxe")
async def buy_pickaxe(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("money", 0) < 1000:
        await call.answer("❌ Недостаточно монет!")
        return
    user["money"] -= 1000
    user["harvest"]["⛏️ Тяпка"] = user["harvest"].get("⛏️ Тяпка", 0) + 1
    await call.answer("✅ Куплена ⛏️ Тяпка!")
    await shop_tools(call)


@router.callback_query(F.data == "buy_tool_worm")
async def buy_worm(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("money", 0) < 500:
        await call.answer("❌ Недостаточно монет!")
        return
    user["money"] -= 500
    user["harvest"]["🪱 Червяк"] = user["harvest"].get("🪱 Червяк", 0) + 1
    await call.answer("✅ Куплен 🪱 Червяк!")
    await shop_tools(call)


@router.callback_query(F.data == "shop_premium")
async def shop_premium(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    text = f"⭐ Премиум магазин\n\nУ вас звёзд: {user.get('stars', 0)}⭐\n\n"
    buttons = []
    for i, item in enumerate(PREMIUM_ITEMS):
        text += f"{item['name']} — {item['price']}⭐\n"
        buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']}⭐",
            callback_data=f"buy_prem_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="🎁 Бесплатный VIP", callback_data="free_vip_request")])
    buttons.append([InlineKeyboardButton(text="⬅️ В магазин", callback_data="shop")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("buy_prem_"))
async def buy_premium(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    idx = int(call.data.replace("buy_prem_", ""))
    if idx >= len(PREMIUM_ITEMS):
        return
    item = PREMIUM_ITEMS[idx]
    if user.get("stars", 0) < item["price"]:
        await call.answer(f"❌ Недостаточно ⭐! Нужно {item['price']}⭐")
        return
    user["stars"] -= item["price"]
    gives = item["gives"]
    if "stars" in gives:
        user["stars"] = user.get("stars", 0) + gives["stars"]
    if "tickets" in gives:
        user["luck_tickets"] = user.get("luck_tickets", 0) + gives["tickets"]
    if "fertilizer" in gives:
        user["harvest"]["💩 Удобрение"] = user["harvest"].get("💩 Удобрение", 0) + gives["fertilizer"]
    if "silage" in gives:
        user["harvest"]["🌿 Силос"] = user["harvest"].get("🌿 Силос", 0) + gives["silage"]
    if "feed" in gives:
        user["harvest"]["🥜 Комбикорм"] = user["harvest"].get("🥜 Комбикорм", 0) + gives["feed"]
    if "wood" in gives:
        user["harvest"]["🪵 древесина"] = user["harvest"].get("🪵 древесина", 0) + gives["wood"]
    if "stone" in gives:
        user["harvest"]["🪨 камень"] = user["harvest"].get("🪨 камень", 0) + gives["stone"]
    if "iron" in gives:
        user["harvest"]["🔗 железо"] = user["harvest"].get("🔗 железо", 0) + gives["iron"]
    if "blueprint" in gives:
        user["harvest"]["📄 чертеж"] = user["harvest"].get("📄 чертеж", 0) + gives["blueprint"]
    if "pickaxe" in gives:
        user["harvest"]["⛏️ Тяпка"] = user["harvest"].get("⛏️ Тяпка", 0) + gives["pickaxe"]
    if "worms" in gives:
        user["harvest"]["🪱 Червяк"] = user["harvest"].get("🪱 Червяк", 0) + gives["worms"]
    await call.answer(f"✅ Куплено {item['name']}!")
    await shop_premium(call)


# ==================== БЕСПЛАТНЫЙ VIP ====================
@router.callback_query(F.data == "free_vip_request")
async def free_vip_request(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("vip_request_pending"):
        await call.answer("⏳ Заявка уже подана! Ожидайте решения.")
        return

    await call.message.edit_text(
        "👑 Бесплатный VIP\n\n"
        "Вы вправду хотите получить VIP подписку?\n\n"
        "Если да, подайте заявление на получение VIP подписки по кнопке ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Подать заявление", callback_data="submit_vip_request")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="shop_premium")],
        ])
    )


@router.callback_query(F.data == "submit_vip_request")
async def submit_vip_request(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    user["vip_request_pending"] = True

    await call.message.edit_text(
        "📝 Заявка подана!\n\n"
        "⏳ Ожидайте решения администратора.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В магазин", callback_data="shop")]
        ])
    )

    # Отправляем админу
    try:
        from config import bot
        await bot.send_message(
            ADMIN_ID,
            f"📬 Новая заявка на VIP!\n\n"
            f"👤 Пользователь: {user['name']}\n"
            f"🆔 ID: {call.from_user.id}\n"
            f"⭐ Уровень: {user.get('level', 1)}\n\n"
            f"Одобрить или отказать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_vip_{call.from_user.id}")],
                [InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_vip_{call.from_user.id}")],
            ])
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")


@router.callback_query(F.data.startswith("approve_vip_"))
async def approve_vip(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только для администратора!")
        return

    user_id = int(call.data.replace("approve_vip_", ""))
    user = get_user(user_id)

    user["vip_request_pending"] = False
    user["vip_until"] = datetime.now() + timedelta(weeks=1)
    user["beds"] = user.get("beds", 2) + 1
    user["beds_data"].append({"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None})

    await call.message.edit_text(
        f"✅ Заявка одобрена!\n\n"
        f"👤 {user['name']} получил VIP на неделю.",
        reply_markup=None
    )

    try:
        from config import bot
        await bot.send_message(
            user_id,
            "🎉 Поздравляем!\n\n"
            "✅ Ваша заявка на VIP одобрена!\n\n"
            "👑 VIP подписка активирована на 7 дней!\n"
            "🌱 Дополнительная грядка добавлена!\n"
            "⚡ Доступны кнопки массового управления!\n\n"
            "👤 Проверьте профиль — /profile",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
            ])
        )
    except:
        pass


@router.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только для администратора!")
        return

    user_id = int(call.data.replace("reject_vip_", ""))
    user = get_user(user_id)
    user["vip_request_pending"] = False

    await call.message.edit_text(
        f"❌ Заявка отклонена.\n\n👤 {user['name']}",
        reply_markup=None
    )

    try:
        from config import bot
        await bot.send_message(
            user_id,
            "😔 К сожалению, ваша заявка на VIP была отклонена.\n\n"
            "Вы можете подать заявку снова позже или купить VIP за ⭐99.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ В премиум магазин", callback_data="shop_premium")]
            ])
        )
    except:
        pass