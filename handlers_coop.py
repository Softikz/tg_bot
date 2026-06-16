import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, bot, users

router = Router()


def init_coop_data():
    if "cooperatives" not in globals():
        global cooperatives
        cooperatives = {}


init_coop_data()


def get_user_coop(user_id: int):
    user = get_user(user_id)
    if "coop_id" not in user:
        return None
    coop_id = user["coop_id"]
    if coop_id not in cooperatives:
        user["coop_id"] = None
        return None
    return cooperatives[coop_id]


def create_coop(name: str, creator_id: int, creator_name: str):
    coop_id = str(len(cooperatives) + 1)
    cooperatives[coop_id] = {
        "id": coop_id,
        "name": name,
        "creator_id": creator_id,
        "members": {
            creator_id: {"name": creator_name, "role": "leader", "joined_at": datetime.now(), "contribution": 0}},
        "level": 1,
        "exp": 0,
        "requests": [],
        "war_energy": 100,
        "war_active": False,
        "war_enemy": None,
        "war_score": 0,
        "created_at": datetime.now(),
    }
    user = get_user(creator_id)
    user["coop_id"] = coop_id
    return cooperatives[coop_id]


@router.callback_query(F.data == "coop")
async def coop_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    coop = get_user_coop(call.from_user.id)

    if not coop:
        text = (
            "🤝 Кооперативы\n\n"
            "Вступайте в кооперативы для совместной игры!\n"
            "• Совместные задания и награды\n"
            "• Войны кооперативов\n"
            "• Обмен ресурсами\n"
            "• Чат с сокомандниками\n\n"
            "Вы не состоите в кооперативе."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти кооператив", callback_data="coop_search")],
            [InlineKeyboardButton(text="🏗️ Создать кооператив", callback_data="coop_create")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
    else:
        members_count = len(coop["members"])
        user_contribution = coop["members"][str(call.from_user.id)]["contribution"]
        text = (
            f"🤝 Кооператив «{coop['name']}»\n\n"
            f"⭐ Уровень: {coop['level']}\n"
            f"🔹 Опыт: {coop['exp']}/{coop['level'] * 1000}\n"
            f"👥 Участников: {members_count}\n"
            f"🏆 Ваш вклад: {user_contribution}\n"
            f"⚔️ Энергия войны: {coop['war_energy']}\n"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Участники", callback_data="coop_members")],
            [InlineKeyboardButton(text="📤 Запросы", callback_data="coop_requests")],
            [InlineKeyboardButton(text="⚔️ Война кооперативов", callback_data="coop_war")],
            [InlineKeyboardButton(text="📦 Обмен ресурсами", callback_data="coop_trade")],
            [InlineKeyboardButton(text="🚪 Покинуть кооператив", callback_data="coop_leave")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "coop_create")
async def coop_create_prompt(call: types.CallbackQuery, state=None):
    user = get_user(call.from_user.id)
    if user.get("coop_id"):
        await call.answer("Вы уже состоите в кооперативе!")
        return
    if user["level"] < 3:
        await call.answer("Кооперативы доступны с 3 уровня!")
        return
    if user["money"] < 10000:
        await call.answer("Недостаточно монет (нужно 10000)!")
        return

    # Создаём кооператив с именем игрока
    user["money"] -= 10000
    coop_name = f"Ферма {user['name']}"
    coop = create_coop(coop_name, call.from_user.id, user["name"])

    await call.message.edit_text(
        f"🏗️ Кооператив «{coop_name}» создан!\n\n"
        f"Приглашайте друзей в свой кооператив!\n"
        f"ID кооператива: {coop['id']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К кооперативу", callback_data="coop")],
        ])
    )


@router.callback_query(F.data == "coop_search")
async def coop_search(call: types.CallbackQuery):
    if not cooperatives:
        await call.answer("Нет доступных кооперативов")
        return

    text = "🔍 Поиск кооперативов\n\n"
    buttons = []
    for coop_id, coop in list(cooperatives.items())[:10]:
        text += f"🏠 {coop['name']} | ⭐{coop['level']} | 👥{len(coop['members'])}\n"
        buttons.append([InlineKeyboardButton(
            text=f"Вступить в «{coop['name']}»",
            callback_data=f"coop_join_{coop_id}"
        )])

    buttons.append([InlineKeyboardButton(text="⬅️ К кооперативам", callback_data="coop")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("coop_join_"))
async def coop_join(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("coop_id"):
        await call.answer("Вы уже в кооперативе!")
        return

    coop_id = call.data.replace("coop_join_", "")
    if coop_id not in cooperatives:
        await call.answer("Кооператив не найден")
        return

    coop = cooperatives[coop_id]
    if len(coop["members"]) >= 20:
        await call.answer("Кооператив заполнен!")
        return

    coop["members"][str(call.from_user.id)] = {
        "name": user["name"],
        "role": "member",
        "joined_at": datetime.now(),
        "contribution": 0
    }
    user["coop_id"] = coop_id
    await call.message.edit_text(
        f"✅ Вы вступили в кооператив «{coop['name']}»!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К кооперативу", callback_data="coop")],
        ])
    )


@router.callback_query(F.data == "coop_members")
async def coop_members(call: types.CallbackQuery):
    coop = get_user_coop(call.from_user.id)
    if not coop:
        await call.answer("Вы не в кооперативе")
        return

    text = f"👥 Участники «{coop['name']}»:\n\n"
    for uid, member in sorted(coop["members"].items(), key=lambda x: x[1]["contribution"], reverse=True):
        role_icon = "👑" if member["role"] == "leader" else "👤"
        text += f"{role_icon} {member['name']} — вклад: {member['contribution']}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К кооперативу", callback_data="coop")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "coop_leave")
async def coop_leave(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    coop = get_user_coop(call.from_user.id)
    if not coop:
        await call.answer("Вы не в кооперативе")
        return

    del coop["members"][str(call.from_user.id)]
    user["coop_id"] = None

    if not coop["members"]:
        del cooperatives[coop["id"]]
    elif str(call.from_user.id) == str(coop["creator_id"]):
        new_leader = list(coop["members"].keys())[0]
        coop["members"][new_leader]["role"] = "leader"
        coop["creator_id"] = int(new_leader)

    await call.message.edit_text(
        "Вы покинули кооператив.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К кооперативам", callback_data="coop")],
        ])
    )


@router.callback_query(F.data == "coop_war")
async def coop_war(call: types.CallbackQuery):
    coop = get_user_coop(call.from_user.id)
    if not coop:
        await call.answer("Вы не в кооперативе")
        return

    if coop["war_active"]:
        text = (
            f"⚔️ Война кооперативов\n\n"
            f"Противник: {coop['war_enemy']}\n"
            f"Ваш счёт: {coop['war_score']}\n"
            f"Энергия: {coop['war_energy']}\n\n"
            "Отправляйте ресурсы для атаки!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать (10⚡)", callback_data="coop_war_attack")],
            [InlineKeyboardButton(text="⬅️ К кооперативу", callback_data="coop")],
        ])
    else:
        other_coops = [c for cid, c in cooperatives.items() if cid != coop["id"] and len(c["members"]) >= 2]
        if not other_coops:
            await call.answer("Нет доступных противников")
            return
        enemy = random.choice(other_coops)
        coop["war_active"] = True
        coop["war_enemy"] = enemy["name"]
        coop["war_score"] = 0
        text = (
            f"⚔️ Война начата!\n\n"
            f"Противник: {enemy['name']}\n"
            f"Отправляйте ресурсы для атаки!\n"
            f"Энергия: {coop['war_energy']}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать (10⚡)", callback_data="coop_war_attack")],
            [InlineKeyboardButton(text="⬅️ К кооперативу", callback_data="coop")],
        ])

    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "coop_war_attack")
async def coop_war_attack(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    coop = get_user_coop(call.from_user.id)
    if not coop or not coop["war_active"]:
        await call.answer("Война не активна")
        return

    if coop["war_energy"] < 10:
        await call.answer("Недостаточно энергии войны!")
        return

    # Требуем ресурсы для атаки
    if user["harvest"].get("🌾 Пшеница", 0) < 50:
        await call.answer("Нужно 50 пшеницы для атаки!")
        return

    user["harvest"]["🌾 Пшеница"] -= 50
    coop["war_energy"] -= 10
    points = random.randint(10, 30)
    coop["war_score"] += points
    coop["members"][str(call.from_user.id)]["contribution"] += points
    coop["exp"] += points

    if coop["war_score"] >= 100:
        coop["war_active"] = False
        user["money"] += 5000
        user["exp"] += 200
        await call.message.edit_text(
            f"🎉 Война выиграна!\n"
            f"Финальный счёт: {coop['war_score']}\n"
            f"💰 Награда: 5000 монет, +200 опыта",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 К кооперативу", callback_data="coop")],
            ])
        )
        return

    await call.message.edit_text(
        f"⚔️ Атака! +{points} очков\n"
        f"Счёт: {coop['war_score']}/100\n"
        f"Энергия: {coop['war_energy']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Атаковать ещё (10⚡)", callback_data="coop_war_attack")],
            [InlineKeyboardButton(text="⬅️ К кооперативу", callback_data="coop")],
        ])
    )