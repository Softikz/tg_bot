import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, bot

router = Router()

FISH_TYPES = {
    1: "🐡 Фугу",
    2: "🦐 Креветка",
    3: "🐟 Карась",
    4: "🐠 Окунь",
    5: "🦈 Щука",
    6: "🐋 Белуга",
}

EQUIPMENT_SLOTS = ["🎩 Головной убор", "👕 Верх", "👖 Штаны", "👟 Обувь", "🧤 Перчатки", "👜 Аксессуар"]
EQUIPMENT_GRADES = ["E", "D", "C", "B", "A"]


def init_fishing_state(user_id: int):
    user = get_user(user_id)
    if "fishing" not in user:
        user["fishing"] = {
            "active": False,
            "darts": [],
            "bonus_dart": None,
            "started_at": None,
            "catch_ready_at": None,
        }
    if "equipment" not in user:
        user["equipment"] = {
            "🎩 Головной убор": None,
            "👕 Верх": None,
            "👖 Штаны": None,
            "👟 Обувь": None,
            "🧤 Перчатки": None,
            "👜 Аксессуар": None,
        }
    if "equipment_inventory" not in user:
        user["equipment_inventory"] = []
    return user["fishing"]


@router.callback_query(F.data == "fishing_enter")
async def fishing_enter(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user["level"] < 5:
        await call.answer("Рыбалка доступна с 5 уровня!")
        return
    if user["harvest"].get("🪱 Червяк", 0) < 1:
        await call.answer("Нужен 1 червяк для рыбалки!")
        return
    user["harvest"]["🪱 Червяк"] -= 1
    fishing = init_fishing_state(call.from_user.id)
    fishing["active"] = True
    fishing["darts"] = []
    fishing["bonus_dart"] = None
    fishing["started_at"] = datetime.now()
    fishing["catch_ready_at"] = None

    await call.message.edit_text(
        "🎣 Рыбалка\n\n"
        "Бросайте дротики! Нажмите на 🔵 чтобы бросить дротик.\n"
        "У вас 3 броска.\n\n"
        "Бросков сделано: 0/3",
        reply_markup=fishing_throw_kb(fishing)
    )


def fishing_throw_kb(fishing: dict):
    throws_done = len(fishing["darts"])
    buttons = []
    if throws_done < 3:
        buttons.append([InlineKeyboardButton(text=f"🔵 Бросок {throws_done + 1}", callback_data="fish_throw")])
    if fishing.get("bonus_dart") is None and throws_done == 3:
        # Можно добавить подкормку для 4-го броска
        buttons.append([InlineKeyboardButton(text="💚 Подкормка (эссенция)", callback_data="fish_bonus")])
    if throws_done >= 3:
        buttons.append([InlineKeyboardButton(text="⏱️ Завершить рыбалку (12ч)", callback_data="fish_finish")])
    buttons.append([InlineKeyboardButton(text="⬅️ Покинуть озеро", callback_data="fishing_leave")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "fish_throw")
async def fish_throw(call: types.CallbackQuery):
    fishing = init_fishing_state(call.from_user.id)
    if not fishing["active"]:
        await call.answer("Рыбалка не активна")
        return
    if len(fishing["darts"]) >= 3 and fishing["bonus_dart"] is None:
        await call.answer("Все броски сделаны")
        return

    dart_value = random.randint(1, 6)
    if len(fishing["darts"]) < 3:
        fishing["darts"].append(dart_value)
    elif fishing["bonus_dart"] is None and len(fishing["darts"]) == 3:
        fishing["bonus_dart"] = dart_value

    throws_done = len(fishing["darts"])
    darts_text = " ".join([FISH_TYPES[d] for d in fishing["darts"]])
    if fishing["bonus_dart"]:
        darts_text += f" + 💚{FISH_TYPES[fishing['bonus_dart']]}"

    await call.message.edit_text(
        f"🎣 Рыбалка\n\n"
        f"🎯 Ваши броски: {darts_text}\n"
        f"Бросков сделано: {throws_done}/3\n\n"
        f"Значения:\n"
        + "\n".join([f"   🎲 {i + 1} → {FISH_TYPES[d]}" for i, d in enumerate(fishing["darts"])])
        + (f"\n   💚 Бонус → {FISH_TYPES[fishing['bonus_dart']]}" if fishing["bonus_dart"] else ""),
        reply_markup=fishing_throw_kb(fishing)
    )


@router.callback_query(F.data == "fish_bonus")
async def fish_bonus(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fishing = init_fishing_state(call.from_user.id)
    # Проверка наличия эссенций (упрощённо — любая эссенция)
    essences = ["💙", "💚", "💛", "💖", "🩷", "❤️‍🔥", "🤍", "🩵"]
    has_essence = False
    for ess in essences:
        if user["harvest"].get(ess, 0) > 0:
            user["harvest"][ess] -= 1
            has_essence = True
            break
    if not has_essence:
        await call.answer("Нужна эссенция для подкормки!")
        return
    fishing["bonus_dart"] = random.randint(1, 6)
    await call.message.edit_text(
        f"💚 Подкормка активирована!\n"
        f"Бонусный бросок: {FISH_TYPES[fishing['bonus_dart']]}\n\n"
        "Нажмите «Завершить рыбалку»",
        reply_markup=fishing_throw_kb(fishing)
    )


@router.callback_query(F.data == "fish_finish")
async def fish_finish(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fishing = init_fishing_state(call.from_user.id)
    if not fishing["active"] or len(fishing["darts"]) < 3:
        await call.answer("Сделайте 3 броска!")
        return

    fishing["catch_ready_at"] = datetime.now() + timedelta(hours=12)
    fishing["active"] = False

    darts = fishing["darts"]
    bonus = fishing["bonus_dart"]
    combo = darts + ([bonus] if bonus else [])

    await call.message.edit_text(
        f"🎣 Рыбалка завершена!\n\n"
        f"Ваша комбинация: {' '.join([FISH_TYPES[d] for d in combo])}\n"
        f"Очки: {''.join(map(str, combo))}\n\n"
        f"⏰ Улов будет готов через 12 часов\n"
        f"🕐 Ожидайте: {fishing['catch_ready_at'].strftime('%H:%M')}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Ускорить (50💰)", callback_data="fish_speed")],
            [InlineKeyboardButton(text="🔄 Перебросить (1🪱)", callback_data="fish_reroll")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data="city")],
        ])
    )
    # Запускаем таймер на выдачу улова
    import asyncio
    asyncio.create_task(fishing_catch_timer(call.from_user.id, fishing))


async def fishing_catch_timer(user_id: int, fishing: dict):
    await asyncio.sleep(12 * 3600)
    user = get_user(user_id)
    fishing = user.get("fishing", {})
    if not fishing.get("catch_ready_at"):
        return
    if datetime.now() < fishing["catch_ready_at"]:
        return

    darts = fishing["darts"]
    bonus = fishing.get("bonus_dart")
    combo = darts + ([bonus] if bonus else [])

    # Определяем награду
    reward = determine_fishing_reward(combo, user_id)
    apply_fishing_reward(user, reward)

    fishing["catch_ready_at"] = None
    fishing["darts"] = []
    fishing["bonus_dart"] = None

    try:
        await bot.send_message(
            user_id,
            f"🎣 Ваш улов готов!\n\n"
            f"Комбинация: {' '.join([FISH_TYPES[d] for d in combo])}\n"
            f"🎁 Награда: {reward['description']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎣 На озеро", callback_data="fishing_enter")],
                [InlineKeyboardButton(text="⬅️ В город", callback_data="city")],
            ])
        )
    except:
        pass


def determine_fishing_reward(combo, user_id):
    """Определяет награду за комбинацию"""
    if len(combo) == 4:
        # С подкормкой
        if len(set(combo)) == 1:
            return {
                "type": "equipment",
                "grade": "D",
                "slot": random.choice(EQUIPMENT_SLOTS),
                "description": f"Экипировка [D]!"
            }
        # Три одинаковых из четырёх
        for val in set(combo):
            if combo.count(val) >= 3:
                return {
                    "type": "equipment",
                    "grade": "E",
                    "slot": random.choice(EQUIPMENT_SLOTS),
                    "description": f"Экипировка [E]!"
                }
        # Обычная рыба
        return {
            "type": "fish",
            "fish": FISH_TYPES[max(combo)],
            "amount": max(combo),
            "description": f"{FISH_TYPES[max(combo)]} x{max(combo)}"
        }

    if len(combo) == 3:
        if len(set(combo)) == 1:
            # Три одинаковых — экипировка [E]
            slot_map = {
                1: "👜 Аксессуар",
                2: "🧤 Перчатки",
                3: "👟 Обувь",
                4: "👖 Штаны",
                5: "👕 Верх",
                6: "🎩 Головной убор",
            }
            slot = slot_map.get(combo[0], random.choice(EQUIPMENT_SLOTS))
            return {
                "type": "equipment",
                "grade": "E",
                "slot": slot,
                "description": f"Экипировка [E] — {slot}!"
            }
        # Обычный улов
        return {
            "type": "fish",
            "fish": FISH_TYPES[max(combo)],
            "amount": max(combo),
            "description": f"{FISH_TYPES[max(combo)]} x{max(combo)}"
        }


def apply_fishing_reward(user: dict, reward: dict):
    if reward["type"] == "fish":
        fish_name = reward["fish"]
        user["harvest"][fish_name] = user["harvest"].get(fish_name, 0) + reward["amount"]
    elif reward["type"] == "equipment":
        item = {
            "slot": reward["slot"],
            "grade": reward["grade"],
        }
        if "equipment_inventory" not in user:
            user["equipment_inventory"] = []
        user["equipment_inventory"].append(item)


@router.callback_query(F.data == "fish_speed")
async def fish_speed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fishing = user.get("fishing", {})
    if not fishing.get("catch_ready_at"):
        await call.answer("Нечего ускорять")
        return
    if user["money"] < 50:
        await call.answer("Недостаточно монет (нужно 50)")
        return
    user["money"] -= 50
    fishing["catch_ready_at"] = datetime.now()
    await call.answer("Улов готов! Нажмите на озеро для сбора")
    await fishing_catch_timer(call.from_user.id, fishing)


@router.callback_query(F.data == "fish_reroll")
async def fish_reroll(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user["harvest"].get("🪱 Червяк", 0) < 1:
        await call.answer("Нужен 1 червяк для переброса!")
        return
    user["harvest"]["🪱 Червяк"] -= 1
    fishing = init_fishing_state(call.from_user.id)
    fishing["active"] = True
    fishing["darts"] = []
    fishing["bonus_dart"] = None
    fishing["started_at"] = datetime.now()
    fishing["catch_ready_at"] = None
    await call.message.edit_text(
        "🔄 Переброс! Новые дротики.\n\nБросков сделано: 0/3",
        reply_markup=fishing_throw_kb(fishing)
    )


@router.callback_query(F.data == "fishing_leave")
async def fishing_leave(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fishing = user.get("fishing", {})
    fishing["active"] = False
    await call.message.edit_text(
        "Вы покинули озеро.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
        ])
    )


@router.callback_query(F.data == "fishing_equipment")
async def fishing_equipment(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if "equipment" not in user:
        user["equipment"] = {slot: None for slot in EQUIPMENT_SLOTS}
    if "equipment_inventory" not in user:
        user["equipment_inventory"] = []

    text = "👕 Экипировка (Домик)\n\n"
    text += "🎯 Шанс двойного сбора:\n"
    for slot in EQUIPMENT_SLOTS:
        eq = user["equipment"].get(slot)
        if eq:
            text += f"{slot}: [{eq['grade']}] — шанс x2: {5 * (EQUIPMENT_GRADES.index(eq['grade']) + 1)}%\n"
        else:
            text += f"{slot}: пусто\n"

    text += f"\n🎒 Инвентарь экипировки: {len(user['equipment_inventory'])} предметов"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Просмотреть инвентарь", callback_data="fish_inventory")],
        [InlineKeyboardButton(text="🔄 Объединить предметы", callback_data="fish_merge")],
        [InlineKeyboardButton(text="⬅️ На озеро", callback_data="fishing_enter")],
        [InlineKeyboardButton(text="⬅️ В город", callback_data="city")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "fish_inventory")
async def fish_inventory(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if "equipment_inventory" not in user:
        user["equipment_inventory"] = []

    inv = user["equipment_inventory"]
    if not inv:
        await call.answer("Инвентарь пуст")
        return

    text = "🎒 Инвентарь экипировки:\n\n"
    for i, item in enumerate(inv):
        text += f"{i + 1}. {item['slot']} [{item['grade']}]\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Надеть предмет", callback_data="fish_equip_select")],
        [InlineKeyboardButton(text="⬅️ К экипировке", callback_data="fishing_equipment")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "fish_merge")
async def fish_merge(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if "equipment_inventory" not in user:
        user["equipment_inventory"] = []

    inv = user["equipment_inventory"]
    # Ищем 3 одинаковых предмета для объединения
    from collections import Counter
    items_by_slot_grade = {}
    for i, item in enumerate(inv):
        key = f"{item['slot']}_{item['grade']}"
        if key not in items_by_slot_grade:
            items_by_slot_grade[key] = []
        items_by_slot_grade[key].append(i)

    merged = False
    for key, indices in items_by_slot_grade.items():
        if len(indices) >= 3:
            slot, grade = key.split("_")
            if grade in EQUIPMENT_GRADES and grade != "A":
                next_grade = EQUIPMENT_GRADES[EQUIPMENT_GRADES.index(grade) + 1]
                cost = {0: 50000, 1: 300000, 2: 1500000, 3: 5000000}[EQUIPMENT_GRADES.index(grade)]
                if user["money"] >= cost:
                    user["money"] -= cost
                    # Удаляем 3 предмета
                    for idx in sorted(indices, reverse=True):
                        inv.pop(idx)
                    # Добавляем улучшенный
                    inv.append({"slot": slot, "grade": next_grade})
                    merged = True
                    await call.answer(f"Объединено! {slot} [{next_grade}]")
                    break
                else:
                    await call.answer(f"Недостаточно монет (нужно {cost})")
                    return

    if not merged:
        await call.answer("Нет 3 одинаковых предметов для объединения")
    else:
        await fish_inventory(call)