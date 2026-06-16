import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user

router = Router()

MINE_ENEMIES = {
    "1-5": [
        {"name": "🦇 Летучие мыши", "damage": 1, "flee_chance": 80},
        {"name": "🐀 Крысы", "damage": 1, "flee_chance": 80},
    ],
    "6-10": [
        {"name": "🕷️ Пауки", "damage": 2, "flee_chance": 60},
        {"name": "🐍 Змеи", "damage": 2, "flee_chance": 60},
        {"name": "👺 Гоблины", "damage": 3, "flee_chance": 60},
        {"name": "💀 Скелеты", "damage": 3, "flee_chance": 60},
    ],
    "11-15": [
        {"name": "🧌 Тролли", "damage": 4, "flee_chance": 40},
        {"name": "😈 Демоны", "damage": 4, "flee_chance": 40},
        {"name": "🐉 Драконы", "damage": 5, "flee_chance": 40},
        {"name": "🗿 Стражи", "damage": 5, "flee_chance": 40},
        {"name": "👻 Призраки", "damage": 3, "flee_chance": 40},
    ],
}

MINE_RESOURCES = {
    "1-5": [
        {"name": "🪨 камень", "chance": 40, "amount": (1, 3)},
        {"name": "💰 монеты", "chance": 60, "amount": (100, 500)},
    ],
    "6-10": [
        {"name": "🪨 камень", "chance": 20, "amount": (2, 5)},
        {"name": "🔗 железо", "chance": 10, "amount": (1, 2)},
        {"name": "💰 монеты", "chance": 70, "amount": (200, 1000)},
    ],
    "11-15": [
        {"name": "🪨 камень", "chance": 30, "amount": (3, 8)},
        {"name": "🔗 железо", "chance": 20, "amount": (2, 4)},
        {"name": "📄 чертежи", "chance": 10, "amount": (1, 1)},
        {"name": "💰 монеты", "chance": 40, "amount": (300, 1500)},
    ],
}

def get_mine_floor_range(floor: int):
    if floor <= 5:
        return "1-5"
    elif floor <= 10:
        return "6-10"
    else:
        return "11-15"

def get_mine_grid_size(floor: int):
    if floor <= 5:
        return 3
    elif floor <= 10:
        return 4
    else:
        return 5

def generate_mine_floor(floor: int):
    size = get_mine_grid_size(floor)
    grid = []
    for i in range(size):
        row = []
        for j in range(size):
            cell_type = random.choices(
                ["empty", "enemy", "resource", "heal", "alchemist"],
                weights=[30, 40, 20, 8, 2]
            )[0]
            row.append({"type": cell_type, "revealed": False, "x": i, "y": j})
        grid.append(row)
    if floor in [5, 10, 15]:
        exit_x = random.randint(0, size - 1)
        exit_y = random.randint(0, size - 1)
        grid[exit_x][exit_y]["type"] = "exit"
    return grid, size

def init_mine_state(user_id: int):
    user = get_user(user_id)
    if "mine" not in user:
        user["mine"] = {
            "active": False,
            "current_floor": 1,
            "lives": 3,
            "max_lives": 3,
            "grid": None,
            "size": 0,
            "position": (0, 0),
            "loot": [],
            "shield_active": False,
            "sword_uses": 0,
            "saved_chest": None,
            "heal_encounters": 0,
            "chem_drops": 0,
        }
    return user["mine"]

def mine_floor_kb(mine_state, size: int):
    grid = mine_state["grid"]
    px, py = mine_state["position"]
    buttons = []
    for i in range(size):
        row = []
        for j in range(size):
            cell = grid[i][j]
            if i == px and j == py:
                text = "🧑‍🌾"
            elif cell["revealed"]:
                if cell["type"] == "empty":
                    text = "⬜"
                elif cell["type"] == "enemy":
                    text = "👹"
                elif cell["type"] == "resource":
                    text = "💎"
                elif cell["type"] == "heal":
                    text = "❤️"
                elif cell["type"] == "alchemist":
                    text = "🧙"
                elif cell["type"] == "exit":
                    text = "🚪"
                else:
                    text = "⬜"
            else:
                text = "⬛"
            row.append(InlineKeyboardButton(text=text, callback_data=f"mine_move_{i}_{j}"))
        buttons.append(row)

    action_buttons = []
    action_buttons.append(InlineKeyboardButton(text="🏃 Покинуть шахту", callback_data="mine_leave"))
    if mine_state.get("sword_uses", 0) > 0:
        action_buttons.append(InlineKeyboardButton(text=f"🗡️ Меч ({mine_state['sword_uses']})", callback_data="mine_noop"))
    if mine_state.get("shield_active"):
        action_buttons.append(InlineKeyboardButton(text="🛡️ Щит активен", callback_data="mine_noop"))
    if mine_state.get("saved_chest"):
        action_buttons.append(InlineKeyboardButton(text="📦 Сундук (выкупить 5000💰)", callback_data="mine_chest"))
    buttons.append(action_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(F.data == "mine_enter")
async def mine_enter(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("level", 1) < 5:
        await call.answer("⛏️ Шахта доступна с 5 уровня!")
        return
    if user["harvest"].get("⛏️ Тяпка", 0) < 1:
        await call.answer("Нужна 1 тяпка ⛏️ для входа в шахту!")
        return

    user["harvest"]["⛏️ Тяпка"] -= 1
    mine_state = init_mine_state(call.from_user.id)
    mine_state["active"] = True
    mine_state["current_floor"] = 1
    mine_state["lives"] = 3
    mine_state["max_lives"] = 3
    mine_state["loot"] = []
    mine_state["position"] = (0, 0)
    mine_state["heal_encounters"] = 0
    mine_state["chem_drops"] = 0

    if user["harvest"].get("🛡️ Щит", 0) > 0:
        mine_state["shield_active"] = True
        mine_state["max_lives"] = 8
        mine_state["lives"] = 8
        user["harvest"]["🛡️ Щит"] -= 1
    else:
        mine_state["shield_active"] = False

    if user["harvest"].get("🗡️ Меч", 0) > 0:
        mine_state["sword_uses"] = 5
        user["harvest"]["🗡️ Меч"] -= 1
    else:
        mine_state["sword_uses"] = 0

    grid, size = generate_mine_floor(1)
    mine_state["grid"] = grid
    mine_state["size"] = size
    grid[0][0]["revealed"] = True

    difficulty = "легкий"
    await call.message.edit_text(
        f"⛏️ Шахта — Этаж 1/15 ({difficulty})\n"
        f"Сетка: {size}x{size}\n"
        f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}\n"
        f"📍 Позиция: (1, 1)\n\n"
        "Перемещайтесь по сетке, нажимая на соседние клетки.",
        reply_markup=mine_floor_kb(mine_state, size)
    )

@router.callback_query(F.data.startswith("mine_move_"))
async def mine_move(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    mine_state = init_mine_state(call.from_user.id)
    if not mine_state["active"]:
        await call.answer("Шахта не активна")
        return

    parts = call.data.split("_")
    new_x = int(parts[2])
    new_y = int(parts[3])
    px, py = mine_state["position"]

    if abs(new_x - px) + abs(new_y - py) != 1:
        await call.answer("Можно ходить только на соседние клетки!")
        return

    mine_state["position"] = (new_x, new_y)
    cell = mine_state["grid"][new_x][new_y]

    if not cell["revealed"]:
        cell["revealed"] = True
        if cell["type"] == "enemy":
            await handle_mine_enemy(call, mine_state, cell)
            return
        elif cell["type"] == "resource":
            await handle_mine_resource(call, mine_state, cell)
            return
        elif cell["type"] == "heal":
            await handle_mine_heal(call, mine_state)
            return
        elif cell["type"] == "alchemist":
            await handle_mine_alchemist(call, mine_state)
            return
        elif cell["type"] == "exit":
            await handle_mine_exit(call, mine_state)
            return

    await update_mine_view(call, mine_state)

async def handle_mine_enemy(call, mine_state, cell):
    floor_range = get_mine_floor_range(mine_state["current_floor"])
    enemies = MINE_ENEMIES[floor_range]
    enemy = random.choice(enemies)

    if mine_state.get("sword_uses", 0) > 0:
        mine_state["sword_uses"] -= 1
        loot = generate_resource_loot(floor_range)
        mine_state["loot"].append(loot)
        if random.random() < 0.5:
            mine_state["chem_drops"] += 1
        await call.message.edit_text(
            f"⚔️ Вы встретили {enemy['name']}!\n"
            f"Вы использовали 🗡️ Меч и победили!\n"
            f"🎁 Добыча: {loot}\n"
            f"Осталось использований меча: {mine_state['sword_uses']}\n"
            f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
            ])
        )
        return

    flee_chance = enemy["flee_chance"]
    if random.randint(1, 100) <= flee_chance:
        await call.message.edit_text(
            f"👹 Вы встретили {enemy['name']}!\n"
            "🏃 Вы успешно убежали!\n"
            f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
            ])
        )
    else:
        mine_state["lives"] -= enemy["damage"]
        if mine_state["lives"] <= 0:
            await handle_mine_death(call, mine_state)
        else:
            await call.message.edit_text(
                f"👹 Вы встретили {enemy['name']}!\n"
                f"🏃 Побег не удался!\n"
                f"💔 Получен урон: {enemy['damage']}\n"
                f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
                ])
            )

async def handle_mine_resource(call, mine_state, cell):
    floor_range = get_mine_floor_range(mine_state["current_floor"])
    loot = generate_resource_loot(floor_range)
    mine_state["loot"].append(loot)
    await call.message.edit_text(
        f"💎 Вы нашли ресурсы!\n🎁 Получено: {loot}\n"
        f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
        ])
    )

async def handle_mine_heal(call, mine_state):
    heal_amount = random.randint(1, 2)
    mine_state["lives"] = min(mine_state["lives"] + heal_amount, mine_state["max_lives"])
    mine_state["heal_encounters"] += 1
    await call.message.edit_text(
        f"❤️ Вы нашли лечебный источник!\n"
        f"Восстановлено жизней: +{heal_amount}\n"
        f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}\n"
        f"🧪 Получен 🩸 образец!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
        ])
    )

async def handle_mine_alchemist(call, mine_state):
    tickets = random.randint(1, 3)
    user = get_user(call.from_user.id)
    user["luck_tickets"] = user.get("luck_tickets", 0) + tickets
    await call.message.edit_text(
        f"🧙 Вы встретили Алхимика-отшельника!\n"
        f"Он даёт вам 🎫 билетов удачи: +{tickets}\n"
        f"Всего билетов: {user['luck_tickets']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
        ])
    )

async def handle_mine_exit(call, mine_state):
    floor = mine_state["current_floor"]
    rewards = {5: 1000, 10: 2000, 15: 3000}
    money = rewards.get(floor, 500)
    user = get_user(call.from_user.id)
    user["money"] = user.get("money", 0) + money

    for loot in mine_state["loot"]:
        apply_loot(user, loot)
    if mine_state["heal_encounters"] > 0:
        user["harvest"]["🩸 образец"] = user["harvest"].get("🩸 образец", 0) + mine_state["heal_encounters"]
    if mine_state["chem_drops"] > 0:
        user["harvest"]["⚗️ химикат"] = user["harvest"].get("⚗️ химикат", 0) + mine_state["chem_drops"]

    mine_state["loot"] = []
    mine_state["heal_encounters"] = 0
    mine_state["chem_drops"] = 0

    if floor < 15:
        mine_state["current_floor"] += 1
        grid, size = generate_mine_floor(mine_state["current_floor"])
        mine_state["grid"] = grid
        mine_state["size"] = size
        mine_state["position"] = (0, 0)
        grid[0][0]["revealed"] = True
        await call.message.edit_text(
            f"🚪 Вы прошли на этаж {mine_state['current_floor']}!\n"
            f"💰 Награда за этаж: {money} монет\n"
            f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить исследование", callback_data="mine_continue")]
            ])
        )
    else:
        mine_state["active"] = False
        await call.message.edit_text(
            f"🏆 Вы прошли всю шахту!\n\n"
            f"💰 Финальная награда: {money} монет\n"
            f"🎁 Все ресурсы сохранены!\n\n"
            f"Поздравляем с прохождением шахты!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
            ])
        )

async def handle_mine_death(call, mine_state):
    user = get_user(call.from_user.id)

    if user["harvest"].get("🇨🇭 Аптечка", 0) > 0:
        user["harvest"]["🇨🇭 Аптечка"] -= 1
        mine_state["lives"] = 1
        await call.message.edit_text(
            "💀 Вы потеряли сознание!\n"
            "🇨🇭 Использована аптечка! +1 жизнь\n"
            "❤️ Жизни: 1",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="mine_continue")]
            ])
        )
        return

    mine_state["saved_chest"] = {
        "loot": mine_state["loot"].copy(),
        "heal_encounters": mine_state["heal_encounters"],
        "chem_drops": mine_state["chem_drops"],
        "floor": mine_state["current_floor"],
    }
    mine_state["active"] = False
    mine_state["loot"] = []
    mine_state["heal_encounters"] = 0
    mine_state["chem_drops"] = 0

    await call.message.edit_text(
        "💀 Врачи нашли вас в шахте без сознания.\n"
        "📦 Твои вещи были перенесены в сундук.\n\n"
        "Вы можете выкупить сундук за 5000💰.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Открыть сундук (5000💰)", callback_data="mine_chest")],
            [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
        ])
    )

@router.callback_query(F.data == "mine_chest")
async def mine_chest(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    mine_state = init_mine_state(call.from_user.id)
    chest = mine_state.get("saved_chest")

    if not chest:
        await call.answer("Сундук пуст")
        return
    if user.get("money", 0) < 5000:
        await call.answer("Недостаточно монет (нужно 5000💰)")
        return

    user["money"] -= 5000
    for loot in chest["loot"]:
        apply_loot(user, loot)
    if chest["heal_encounters"] > 0:
        user["harvest"]["🩸 образец"] = user["harvest"].get("🩸 образец", 0) + chest["heal_encounters"]
    if chest["chem_drops"] > 0:
        user["harvest"]["⚗️ химикат"] = user["harvest"].get("⚗️ химикат", 0) + chest["chem_drops"]

    mine_state["saved_chest"] = None

    await call.message.edit_text(
        "📦 Сундук выкуплен!\n\n"
        "Все ресурсы возвращены в инвентарь.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
        ])
    )

@router.callback_query(F.data == "mine_leave")
async def mine_leave(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    mine_state = init_mine_state(call.from_user.id)

    if user["harvest"].get("🧊 Эвакуационная капсула", 0) > 0:
        user["harvest"]["🧊 Эвакуационная капсула"] -= 1
        for loot in mine_state["loot"]:
            apply_loot(user, loot)
        if mine_state["heal_encounters"] > 0:
            user["harvest"]["🩸 образец"] = user["harvest"].get("🩸 образец", 0) + mine_state["heal_encounters"]
        if mine_state["chem_drops"] > 0:
            user["harvest"]["⚗️ химикат"] = user["harvest"].get("⚗️ химикат", 0) + mine_state["chem_drops"]
        mine_state["active"] = False
        mine_state["loot"] = []
        await call.message.edit_text(
            "🧊 Капсула активирована! Все ресурсы сохранены!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
            ])
        )
    else:
        mine_state["active"] = False
        mine_state["loot"] = []
        await call.message.edit_text(
            "🏃 Вы покинули шахту. Несохранённые ресурсы утеряны.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В город", callback_data="city")]
            ])
        )

@router.callback_query(F.data == "mine_continue")
async def mine_continue(call: types.CallbackQuery):
    mine_state = init_mine_state(call.from_user.id)
    if not mine_state["active"]:
        await call.answer("Шахта не активна")
        return
    await update_mine_view(call, mine_state)

async def update_mine_view(call, mine_state):
    floor = mine_state["current_floor"]
    size = mine_state["size"]
    px, py = mine_state["position"]
    if floor <= 5:
        difficulty = "легкий"
    elif floor <= 10:
        difficulty = "средний"
    else:
        difficulty = "сложный"
    await call.message.edit_text(
        f"⛏️ Шахта — Этаж {floor}/15 ({difficulty})\n"
        f"Сетка: {size}x{size}\n"
        f"❤️ Жизни: {mine_state['lives']}/{mine_state['max_lives']}\n"
        f"📍 Позиция: ({px+1}, {py+1})\n"
        f"📦 Добычи собрано: {len(mine_state['loot'])}",
        reply_markup=mine_floor_kb(mine_state, size)
    )

def generate_resource_loot(floor_range: str):
    resources = MINE_RESOURCES[floor_range]
    total = sum(r["chance"] for r in resources)
    roll = random.randint(1, total)
    cumulative = 0
    for res in resources:
        cumulative += res["chance"]
        if roll <= cumulative:
            amount = random.randint(res["amount"][0], res["amount"][1])
            return f"{res['name']} x{amount}"
    return "💰 монеты x100"

def apply_loot(user: dict, loot: str):
    parts = loot.split(" x")
    if len(parts) != 2:
        return
    item = parts[0]
    try:
        amount = int(parts[1])
    except:
        return
    if "монеты" in item:
        user["money"] = user.get("money", 0) + amount
    else:
        user["harvest"][item] = user["harvest"].get(item, 0) + amount

@router.callback_query(F.data == "mine_noop")
async def mine_noop(call: types.CallbackQuery):
    await call.answer("Информация об экипировке")