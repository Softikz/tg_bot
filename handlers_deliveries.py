from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user
from datetime import datetime

router = Router()

ALL_QUESTS = [
    {
        "id": "first_harvest",
        "chapter": 1,
        "name": "Первое знакомство",
        "description": "Собери 3 урожая",
        "target": 3,
        "task_type": "harvest",
        "reward": {"money": 200, "stars": 2, "exp": 20},
        "start_resources": {"🥕": 3},
    },
    {
        "id": "first_money",
        "chapter": 1,
        "name": "Первые деньги",
        "description": "Заработай 500 монет",
        "target": 500,
        "task_type": "earn",
        "reward": {"money": 100, "stars": 1, "exp": 15},
    },
    {
        "id": "sell_10",
        "chapter": 1,
        "name": "Торговец",
        "description": "Продай 10 любых овощей",
        "target": 10,
        "task_type": "sell",
        "reward": {"money": 300, "stars": 2, "exp": 25},
    },
    {
        "id": "plant_variety",
        "chapter": 1,
        "name": "Разнообразие",
        "description": "Посади 3 разных вида культур",
        "target": 3,
        "task_type": "plant_variety",
        "reward": {"money": 400, "stars": 3, "exp": 30},
        "start_resources": {"🧅": 5, "🥔": 5},
    },
]


def get_user_quests(user_id: int):
    user = get_user(user_id)
    if "quests" not in user:
        user["quests"] = {
            "completed": [],
            "active": None,
            "progress": {},
            "planted_types": [],
        }
    return user["quests"]


@router.callback_query(F.data == "deliveries")
async def deliveries_list(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    text = (
        "🧔🏻 Председатель СНТ - Доставки\n\n"
        "📦 Доступны доставки на сегодня:\n\n"
        "Выберите доставку для просмотра деталей:\n\n"
        "⏰ Доставки обновляются каждый день в 6:00\n"
        "✅ Каждую доставку можно выполнить только один раз в день"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Заготовка кормов", callback_data="deliv_feed")],
        [InlineKeyboardButton(text="📦 Поиск белка", callback_data="deliv_protein")],
        [InlineKeyboardButton(text="📦 Срочный заказ", callback_data="deliv_urgent")],
        [InlineKeyboardButton(text="🧔🏻 Назад к председателю", callback_data="chairman")]
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "deliv_feed")
async def delivery_feed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🥔": 20, "🧅": 20, "🌾": 5}

    text = (
        "🧔🏻 Доставка: Заготовка кормов\n\n"
        "📝 Приготовление силоса для животных\n\n"
        "📋 Требуется:\n"
    )
    all_enough = True
    for crop, need in required.items():
        have = user["harvest"].get(crop, 0)
        status = "✅" if have >= need else "❌"
        if have < need:
            all_enough = False
        text += f"{status} {crop} x{need} (у вас: {have})\n"

    text += "\n🎁 Награда:\n🌿 2x Силос\n🔹 +50 опыта\n\n"

    if all_enough:
        text += "✅ Достаточно ресурсов для сдачи"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить доставку", callback_data="do_deliv_feed")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    else:
        text += "❌ Недостаточно ресурсов"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Недостаточно ресурсов", callback_data="no_res")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "deliv_protein")
async def delivery_protein(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🥕": 30, "🥦": 10, "🌽": 10}

    text = (
        "🧔🏻 Доставка: Поиск белка\n\n"
        "📝 Сбор белковых продуктов\n\n"
        "📋 Требуется:\n"
    )
    all_enough = True
    for crop, need in required.items():
        have = user["harvest"].get(crop, 0)
        status = "✅" if have >= need else "❌"
        if have < need:
            all_enough = False
        text += f"{status} {crop} x{need} (у вас: {have})\n"

    text += "\n🎁 Награда:\n🌿 2x Силос\n💩 1x Удобрение\n🔹 +100 опыта\n\n"

    if all_enough:
        text += "✅ Достаточно ресурсов для сдачи"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить доставку", callback_data="do_deliv_protein")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    else:
        text += "❌ Недостаточно ресурсов"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Недостаточно ресурсов", callback_data="no_res")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "deliv_urgent")
async def delivery_urgent(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🍓": 15, "🍇": 10}

    text = (
        "🧔🏻 Доставка: Срочный заказ\n\n"
        "📝 Срочная доставка ягод\n\n"
        "📋 Требуется:\n"
    )
    all_enough = True
    for crop, need in required.items():
        have = user["harvest"].get(crop, 0)
        status = "✅" if have >= need else "❌"
        if have < need:
            all_enough = False
        text += f"{status} {crop} x{need} (у вас: {have})\n"

    text += "\n🎁 Награда:\n⭐ 5x Звёзд\n🎫 2x Билета\n🔹 +200 опыта\n\n"

    if all_enough:
        text += "✅ Достаточно ресурсов для сдачи"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить доставку", callback_data="do_deliv_urgent")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    else:
        text += "❌ Недостаточно ресурсов"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Недостаточно ресурсов", callback_data="no_res")],
            [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
        ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "do_deliv_feed")
async def do_deliv_feed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🥔": 20, "🧅": 20, "🌾": 5}
    for crop, need in required.items():
        if user["harvest"].get(crop, 0) < need:
            await call.answer("Недостаточно ресурсов!")
            return
        user["harvest"][crop] -= need
    user["harvest"]["🌿 Силос"] = user["harvest"].get("🌿 Силос", 0) + 2
    user["exp"] = user.get("exp", 0) + 50
    await call.message.edit_text("✅ Доставка выполнена!\n\n🎁 Получено: 🌿 2x Силос, +50 опыта",
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                     [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
                                 ]))


@router.callback_query(F.data == "do_deliv_protein")
async def do_deliv_protein(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🥕": 30, "🥦": 10, "🌽": 10}
    for crop, need in required.items():
        if user["harvest"].get(crop, 0) < need:
            await call.answer("Недостаточно ресурсов!")
            return
        user["harvest"][crop] -= need
    user["harvest"]["🌿 Силос"] = user["harvest"].get("🌿 Силос", 0) + 2
    user["harvest"]["💩 Удобрение"] = user["harvest"].get("💩 Удобрение", 0) + 1
    user["exp"] = user.get("exp", 0) + 100
    await call.message.edit_text("✅ Доставка выполнена!\n\n🎁 Получено: 🌿 2x Силос, 💩 1x Удобрение, +100 опыта",
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                     [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
                                 ]))


@router.callback_query(F.data == "do_deliv_urgent")
async def do_deliv_urgent(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    required = {"🍓": 15, "🍇": 10}
    for crop, need in required.items():
        if user["harvest"].get(crop, 0) < need:
            await call.answer("Недостаточно ресурсов!")
            return
        user["harvest"][crop] -= need
    user["stars"] = user.get("stars", 0) + 5
    user["luck_tickets"] = user.get("luck_tickets", 0) + 2
    user["exp"] = user.get("exp", 0) + 200
    await call.message.edit_text("✅ Доставка выполнена!\n\n🎁 Получено: ⭐ 5x Звёзд, 🎫 2x Билета, +200 опыта",
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                     [InlineKeyboardButton(text="📦 К списку доставок", callback_data="deliveries")]
                                 ]))


@router.callback_query(F.data == "no_res")
async def no_res(call: types.CallbackQuery):
    await call.answer("❌ Недостаточно ресурсов!")


# ==================== ЗАВХОЗ СНТ ====================
@router.callback_query(F.data == "zavhoz")
async def zavhoz_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    quests = get_user_quests(call.from_user.id)

    if quests.get("active"):
        quest = next((q for q in ALL_QUESTS if q["id"] == quests["active"]), None)
        if quest:
            progress = quests["progress"].get(quest["id"], 0)
            target = quest["target"]
            percent = round(progress / target * 100) if target > 0 else 0

            if progress >= target:
                text = (
                    f"👵🏻 Завхоз СНТ: Хм... Не ожидала, признаюсь.\n\n"
                    f"Вот, держи за старания.\n"
                    f"-------------------------\n"
                    f"✅ Задание выполнено!\n\n"
                    f"🎁 Награда:\n"
                    f"💰 {quest['reward']['money']} монет\n"
                    f"⭐ {quest['reward'].get('stars', 0)} звёзд\n"
                    f"🔹 +{quest['reward']['exp']} опыта"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎁 Получить награду", callback_data="claim_quest")],
                    [InlineKeyboardButton(text="⬅️ К завхозу", callback_data="zavhoz")]
                ])
            else:
                text = (
                    f"👵🏻 Завхоз СНТ: Иди работай!\n"
                    f"-------------------------\n"
                    f"📊 Прогресс: {progress}/{target} ({percent}%)\n"
                    f"Продолжай работать!"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Проверить прогресс", callback_data="check_quest")],
                    [InlineKeyboardButton(text="⬅️ К Завхозу", callback_data="zavhoz")]
                ])
            await call.message.edit_text(text, reply_markup=kb)
            return

    completed = len(quests.get("completed", []))
    total = len(ALL_QUESTS)

    if completed >= total:
        text = f"👵🏻 ЗАВХОЗ СНТ\n\n🎉 Все задания выполнены!\n📊 Прогресс: {completed}/{total}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К председателю", callback_data="chairman")]
        ])
        await call.message.edit_text(text, reply_markup=kb)
        return

    next_quest = None
    for q in ALL_QUESTS:
        if q["id"] not in quests.get("completed", []):
            next_quest = q
            break

    if next_quest:
        text = (
            f"👵🏻 ЗАВХОЗ СНТ\n\n"
            f"📋 Доступно задание: {next_quest['name']}\n\n"
            f"📊 Прогресс: {completed}/{total} квестов"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Взять задание", callback_data=f"take_quest_{next_quest['id']}")],
            [InlineKeyboardButton(text="⬅️ К председателю", callback_data="chairman")]
        ])
    else:
        text = f"👵🏻 ЗАВХОЗ СНТ\n\nНет доступных заданий."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К председателю", callback_data="chairman")]
        ])

    await call.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("take_quest_"))
async def take_quest(call: types.CallbackQuery):
    quest_id = call.data.replace("take_quest_", "")
    user = get_user(call.from_user.id)
    quests = get_user_quests(call.from_user.id)

    if quests.get("active"):
        await call.answer("Уже есть активное задание!")
        return

    quest = next((q for q in ALL_QUESTS if q["id"] == quest_id), None)
    if not quest:
        await call.answer("Задание не найдено")
        return

    quests["active"] = quest_id
    quests["progress"] = {quest_id: 0}
    quests["planted_types"] = []

    if "start_resources" in quest:
        for seed, amount in quest["start_resources"].items():
            user["seeds"][seed] = user["seeds"].get(seed, 0) + amount

    text = (
        f"👵🏻 Завхоз СНТ: Вот тебе задание.\n\n"
        f"📋 Задание: {quest['description']}\n\n"
        f"🎁 Награда за выполнение:\n"
        f"{quest['reward']['money']} монет\n"
        f"{quest['reward'].get('stars', 0)} звёзд\n"
        f"{quest['reward']['exp']} опыта\n\n"
        f"Прогресс: 0/{quest['target']} (0%)\n"
        f"Продолжай работать!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить прогресс", callback_data="check_quest")],
        [InlineKeyboardButton(text="⬅️ К Завхозу", callback_data="zavhoz")]
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "check_quest")
async def check_quest(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    quests = get_user_quests(call.from_user.id)

    if not quests.get("active"):
        await call.answer("Нет активного задания")
        await zavhoz_main(call)
        return

    quest = next((q for q in ALL_QUESTS if q["id"] == quests["active"]), None)
    if not quest:
        await zavhoz_main(call)
        return

    progress = quests["progress"].get(quest["id"], 0)
    target = quest["target"]
    percent = round(progress / target * 100) if target > 0 else 0

    if progress >= target:
        await call.message.edit_text(
            f"👵🏻 Завхоз СНТ: Хм... Не ожидала.\n\n"
            f"-------------------------\n"
            f"✅ Задание выполнено!\n\n"
            f"🎁 Награда:\n"
            f"{quest['reward']['money']} монет\n"
            f"{quest['reward'].get('stars', 0)} звёзд\n"
            f"{quest['reward']['exp']} опыта",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Получить награду", callback_data="claim_quest")],
                [InlineKeyboardButton(text="⬅️ К завхозу", callback_data="zavhoz")]
            ])
        )
    else:
        await call.message.edit_text(
            f"👵🏻 Завхоз СНТ: Иди работай!\n"
            f"-------------------------\n"
            f"Прогресс: {progress}/{target} ({percent}%)\n"
            f"Продолжай работать!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить прогресс", callback_data="check_quest")],
                [InlineKeyboardButton(text="⬅️ К Завхозу", callback_data="zavhoz")]
            ])
        )


@router.callback_query(F.data == "claim_quest")
async def claim_quest(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    quests = get_user_quests(call.from_user.id)

    if not quests.get("active"):
        await call.answer("Нет активного задания")
        return

    quest = next((q for q in ALL_QUESTS if q["id"] == quests["active"]), None)
    if not quest:
        return

    # Выдаём награду
    user["money"] = user.get("money", 0) + quest["reward"]["money"]
    user["stars"] = user.get("stars", 0) + quest["reward"].get("stars", 0)
    user["exp"] = user.get("exp", 0) + quest["reward"]["exp"]

    quests["completed"].append(quest["id"])
    quests["active"] = None
    quests["progress"] = {}
    quests["planted_types"] = []

    completed = len(quests["completed"])
    total = len(ALL_QUESTS)

    next_quest = None
    for q in ALL_QUESTS:
        if q["id"] not in quests["completed"]:
            next_quest = q
            break

    text = (
        f"✅ Квест завершен!\n\n"
        f"{quest['name']}\n\n"
        f"Получено:\n"
        f"{quest['reward']['money']} монет\n"
        f"{quest['reward'].get('stars', 0)} звёзд\n"
        f"{quest['reward']['exp']} опыта"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if next_quest:
        text += f"\n\n➡️ Следующее: {next_quest['name']}"
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="➡️ Следующее задание", callback_data=f"take_quest_{next_quest['id']}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ К завхозу", callback_data="zavhoz")])

    await call.message.edit_text(text, reply_markup=kb)


def update_quest_progress(user_id: int, task_type: str, amount: int = 1):
    """Вызывается из других обработчиков для обновления прогресса квестов"""
    user = get_user(user_id)
    quests = get_user_quests(user_id)
    if not quests.get("active"):
        return

    quest = next((q for q in ALL_QUESTS if q["id"] == quests["active"]), None)
    if not quest or quest["task_type"] != task_type:
        return

    if quest["id"] not in quests["progress"]:
        quests["progress"][quest["id"]] = 0
    quests["progress"][quest["id"]] += amount