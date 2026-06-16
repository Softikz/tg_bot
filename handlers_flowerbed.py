import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user

router = Router()

FLOWERS = {
    "🌼 Маргаритка": {"honey": 1, "grow_time": 24, "cost": 100},
    "🌻 Подсолнух": {"honey": 2, "grow_time": 48, "cost": 500},
    "🌹 Роза": {"honey": 3, "grow_time": 72, "cost": 1000},
    "🪷 Лотос": {"honey": 4, "grow_time": 96, "cost": 5000},
    "🌸 Сакура": {"honey": 5, "grow_time": 120, "cost": 10000},
}

def init_flowerbed(user_id: int):
    user = get_user(user_id)
    if "flowerbed" not in user:
        user["flowerbed"] = {
            "slots": [None, None, None],
            "planted_at": [None, None, None],
            "honey": 0,
            "sculptures": [],
            "bee_bonus": 0,
            "bee_bonus_uses": 0,
        }
    return user["flowerbed"]

def get_flowerbed_text(user_id: int):
    user = get_user(user_id)
    fb = init_flowerbed(user_id)
    now = datetime.now()

    text = "🌸 Клумба\n\n"
    for i in range(3):
        flower = fb["slots"][i]
        planted = fb["planted_at"][i]
        if flower and planted:
            if isinstance(planted, str):
                planted = datetime.fromisoformat(planted)
            elapsed = (now - planted).total_seconds() / 3600
            grow_time = FLOWERS[flower]["grow_time"]
            if elapsed >= grow_time:
                text += f"Слот {i+1}: {flower} — 🌸 Цветёт!\n"
            else:
                remain = grow_time - elapsed
                text += f"Слот {i+1}: {flower} — 🌱 Растёт ({int(remain)}ч)\n"
        else:
            text += f"Слот {i+1}: пусто\n"

    text += f"\n🍯 Мёд: {fb.get('honey', 0)}\n"

    if fb.get("bee_bonus_uses", 0) > 0:
        text += f"🐝 Бонус пчёл: активен (x1.5 мёда, ещё {fb['bee_bonus_uses']} сбора)\n"
    else:
        text += "🐝 Бонус пчёл: нет\n"

    if fb.get("sculptures"):
        sculpture_positions = [p+1 for p in fb["sculptures"]]
        text += f"🗿 Скульптуры: в слотах {', '.join(map(str, sculpture_positions))} (+1🍯 соседним цветкам)\n"

    return text

@router.callback_query(F.data == "flowerbed")
async def flowerbed_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)

    text = get_flowerbed_text(call.from_user.id)

    slot_names = []
    for i in range(3):
        if fb["slots"][i]:
            flower = fb["slots"][i]
            planted = fb["planted_at"][i]
            if planted:
                if isinstance(planted, str):
                    planted = datetime.fromisoformat(planted)
                elapsed = (datetime.now() - planted).total_seconds() / 3600
                if elapsed >= FLOWERS[flower]["grow_time"]:
                    slot_names.append(f"Слот {i+1}: {flower} — Цветёт")
                else:
                    slot_names.append(f"Слот {i+1}: {flower} — Растёт")
            else:
                slot_names.append(f"Слот {i+1}: {flower}")
        else:
            slot_names.append(f"Слот {i+1}: пусто")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=slot_names[0], callback_data="flower_plant_0")],
        [InlineKeyboardButton(text=slot_names[1], callback_data="flower_plant_1")],
        [InlineKeyboardButton(text=slot_names[2], callback_data="flower_plant_2")],
        [InlineKeyboardButton(text="🍯 Собрать мёд", callback_data="flower_collect")],
        [InlineKeyboardButton(text="🗿 Установить скульптуру", callback_data="flower_sculpture")],
        [InlineKeyboardButton(text="🐝 Подкормка пчёл (эссенция)", callback_data="flower_bee_bonus")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("flower_plant_"))
async def flower_plant(call: types.CallbackQuery):
    slot = int(call.data.replace("flower_plant_", ""))
    fb = init_flowerbed(call.from_user.id)

    if fb["slots"][slot] and fb["planted_at"][slot]:
        flower = fb["slots"][slot]
        planted = fb["planted_at"][slot]
        if isinstance(planted, str):
            planted = datetime.fromisoformat(planted)
        elapsed = (datetime.now() - planted).total_seconds() / 3600
        if elapsed >= FLOWERS[flower]["grow_time"]:
            await call.answer(f"{flower} уже цветёт! Соберите мёд.")
            return
        else:
            remain = FLOWERS[flower]["grow_time"] - elapsed
            await call.answer(f"Цветок ещё растёт! Осталось {int(remain)}ч")
            return

    text = f"🌸 Посадка в слот {slot + 1}\n\nВыберите цветок:\n"
    buttons = []
    for flower, data in FLOWERS.items():
        have_seeds = user_has_flower_seeds(call.from_user.id, flower)
        cost = data["cost"]
        if have_seeds:
            btn_text = f"{flower} — Посадить"
        else:
            btn_text = f"{flower} — Купить ({cost}💰)"

        text += f"{flower} — 🍯{data['honey']} мёда, ⏰{data['grow_time']}ч, 💰{cost}"
        if have_seeds:
            text += " (есть семена)"
        else:
            text += f" (купить за {cost}💰)"
        text += "\n"

        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"flower_buy_{slot}_{flower}"
        )])

    buttons.append([InlineKeyboardButton(text="⬅️ К клумбе", callback_data="flowerbed")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

def user_has_flower_seeds(user_id: int, flower: str):
    user = get_user(user_id)
    seed_map = {
        "🌼 Маргаритка": "🌼 Семена маргаритки",
        "🌻 Подсолнух": "🌻 Семена подсолнуха",
        "🌹 Роза": "🌹 Семена розы",
        "🪷 Лотос": "🪷 Семена лотоса",
        "🌸 Сакура": "🌸 Семена сакуры",
    }
    seed_name = seed_map.get(flower)
    if seed_name:
        return user.get("seeds", {}).get(seed_name, 0) > 0
    return False

@router.callback_query(F.data.startswith("flower_buy_"))
async def flower_buy(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)
    parts = call.data.split("_")
    slot = int(parts[2])
    flower = "_".join(parts[3:])

    if flower not in FLOWERS:
        await call.answer("Цветок не найден")
        return

    have_seeds = user_has_flower_seeds(call.from_user.id, flower)

    if have_seeds:
        # Используем семена
        seed_map = {
            "🌼 Маргаритка": "🌼 Семена маргаритки",
            "🌻 Подсолнух": "🌻 Семена подсолнуха",
            "🌹 Роза": "🌹 Семена розы",
            "🪷 Лотос": "🪷 Семена лотоса",
            "🌸 Сакура": "🌸 Семена сакуры",
        }
        seed_name = seed_map[flower]
        user["seeds"][seed_name] -= 1
    else:
        cost = FLOWERS[flower]["cost"]
        if user.get("money", 0) < cost:
            await call.answer(f"Недостаточно монет (нужно {cost}💰)")
            return
        user["money"] -= cost

    fb["slots"][slot] = flower
    fb["planted_at"][slot] = datetime.now()

    await call.answer(f"Посажен {flower}!")
    await flowerbed_main(call)

@router.callback_query(F.data == "flower_collect")
async def flower_collect(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)
    now = datetime.now()

    total_honey = 0
    collected = []
    for i in range(3):
        flower = fb["slots"][i]
        planted = fb["planted_at"][i]
        if flower and planted:
            if isinstance(planted, str):
                planted = datetime.fromisoformat(planted)
            elapsed = (now - planted).total_seconds() / 3600
            if elapsed >= FLOWERS[flower]["grow_time"]:
                honey = FLOWERS[flower]["honey"]
                # Бонус от скульптур
                if fb.get("sculptures"):
                    for sculp_pos in fb["sculptures"]:
                        if abs(sculp_pos - i) == 1:
                            honey += 1
                total_honey += honey
                collected.append(flower)
                fb["slots"][i] = None
                fb["planted_at"][i] = None

    if total_honey == 0:
        await call.answer("Нет цветущих цветов для сбора!")
        return

    # Бонус пчёл
    if fb.get("bee_bonus_uses", 0) > 0:
        total_honey = int(total_honey * 1.5)
        fb["bee_bonus_uses"] -= 1

    fb["honey"] = fb.get("honey", 0) + total_honey
    user["exp"] = user.get("exp", 0) + total_honey * 10

    await call.message.edit_text(
        f"🍯 Собрано мёда: +{total_honey}\n"
        f"Собрано с: {', '.join(collected)}\n"
        f"Всего мёда: {fb['honey']}\n"
        f"🔹 Опыт: +{total_honey * 10}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌸 К клумбе", callback_data="flowerbed")],
        ])
    )

@router.callback_query(F.data == "flower_sculpture")
async def flower_sculpture(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)

    if user["harvest"].get("🗿 Скульптура", 0) < 1:
        await call.answer("Нет скульптур! Создайте в кузнице (уровень 3).")
        return

    if len(fb.get("sculptures", [])) >= 3:
        await call.answer("Максимум 3 скульптуры!")
        return

    buttons = []
    for i in range(3):
        if i not in fb.get("sculptures", []):
            buttons.append([InlineKeyboardButton(
                text=f"Установить в слот {i+1}",
                callback_data=f"flower_set_sculpture_{i}"
            )])
    buttons.append([InlineKeyboardButton(text="⬅️ К клумбе", callback_data="flowerbed")])
    await call.message.edit_text(
        "🗿 Установка скульптуры\n\n"
        "Скульптура даёт +1🍯 соседним цветкам.\n"
        "Бонус работает для цветов с медосбором 1-3 (макс до 4).\n"
        "🪷 Лотос (4🍯) не получает бонус от статуй.\n\n"
        "Выберите слот:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("flower_set_sculpture_"))
async def flower_set_sculpture(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)
    pos = int(call.data.replace("flower_set_sculpture_", ""))

    if user["harvest"].get("🗿 Скульптура", 0) < 1:
        await call.answer("Нет скульптур!")
        return

    user["harvest"]["🗿 Скульптура"] -= 1
    if "sculptures" not in fb:
        fb["sculptures"] = []
    fb["sculptures"].append(pos)

    await call.answer("Скульптура установлена!")
    await flowerbed_main(call)

@router.callback_query(F.data == "flower_bee_bonus")
async def flower_bee_bonus(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    fb = init_flowerbed(call.from_user.id)

    # Проверяем наличие подкормки для пчёл
    if user["harvest"].get("🧇 Подкормка для пчел синяя", 0) > 0:
        user["harvest"]["🧇 Подкормка для пчел синяя"] -= 1
        fb["bee_bonus_uses"] = 3
        await call.answer("🐝 Бонус пчёл активирован! Следующие 3 сбора x1.5 мёда.")
    elif user["harvest"].get("🧇 Подкормка для пчел пламенная", 0) > 0:
        user["harvest"]["🧇 Подкормка для пчел пламенная"] -= 1
        fb["bee_bonus_uses"] = 3
        await call.answer("🐝 Бонус пчёл активирован! Следующие 3 сбора x1.5 мёда.")
    else:
        await call.answer("Нет подкормки для пчёл! Создайте в Жирмолкомбинате (уровень 3).")
        return

    await flowerbed_main(call)