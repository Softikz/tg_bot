# handlers/commands.py
import time
import logging
import asyncio
import hashlib
from typing import Dict

from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from storage.db import DB
from game.logic import (
    apply_offline_gain,
    cost_for_upgrade,
    effective_per_click,
    GOLD_DURATION,
    has_active_gold,
    has_active_event,
    calculate_per_click,
    calculate_per_second,
    parse_event_duration,
    get_rebirth_requirement,
    get_rebirth_reward
)

router = Router()
db = DB()
ADMIN_PASSWORD = "sm10082x3%"
ADMIN_ID = 5748972158
log = logging.getLogger(__name__)

# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_bananas_amount = State()
    waiting_for_event_type = State()
    waiting_for_event_duration = State()

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_password = State()
    waiting_for_login = State()

# Список доступных ивентов
AVAILABLE_EVENTS = {
    "event_update_2x": {"name": "🎉 Ивент в честь обновления x2", "multiplier": 2.0},
    "event_update_3x": {"name": "🎊 Ивент в честь обновления x3", "multiplier": 3.0},
    "event_update_5x": {"name": "🚀 Ивент в честь обновления x5", "multiplier": 5.0},
    "event_weekend_2x": {"name": "🎯 Выходной ивент x2", "multiplier": 2.0},
    "event_special_4x": {"name": "💎 Специальный ивент x4", "multiplier": 4.0}
}

# --------------------- УТИЛИТЫ ---------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def is_nickname_taken(nickname: str) -> bool:
    users = db.all_users()
    for user in users:
        if user.get("nickname", "").lower() == nickname.lower():
            return True
    return False

def get_user_by_nickname(nickname: str):
    users = db.all_users()
    for user in users:
        if user.get("nickname", "").lower() == nickname.lower():
            return user
    return None

def ensure_and_update_offline(user_id: int):
    user = db.get_user(user_id)
    if not user:
        return None
    added, new_last = apply_offline_gain(user)
    if added:
        new_bananas = user.get("bananas", 0) + added
        db.update_user(user_id, bananas=new_bananas, last_update=new_last)
    return db.get_user(user_id)

def create_progress_bar(current: int, total: int, size: int = 10) -> str:
    percentage = min(100, int(current / total * 100)) if total > 0 else 100
    filled = int(size * percentage / 100)
    empty = size - filled
    return "🟩" * filled + "⬜" * empty + f" {percentage}%"

def profile_text(user: Dict) -> str:
    nickname = user.get('nickname', 'Неизвестно')
    text = (
        f"👤 Профиль {nickname}\n\n"
        f"🍌 Бананы: {int(user['bananas'])}\n"
        f"🖱 За клик: {effective_per_click(user)}\n"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
    )
    boosts = []
    if has_active_gold(user):
        remaining = int(user.get("gold_expires", 0) - time.time())
        boosts.append(f"✨ Золотой банан (2×) - {remaining} сек")
    if has_active_event(user):
        remaining = int(user.get("event_expires", 0) - time.time())
        multiplier = user.get("event_multiplier", 1.0)
        event_type = user.get("event_type", "")
        boosts.append(f"🎯 {event_type} ({multiplier}×) - {remaining} сек")
    if boosts:
        text += "\n⚡ Активные бусты:\n" + "\n".join(f"• {boost}" for boost in boosts) + "\n"
    text += f"🔁 Перерождений всего: {user.get('rebirths', 0)}\n"
    upgrades = user.get("upgrades", {})
    text += f"\n📊 Улучшения:\n"
    text += f"• Клик: уровень {upgrades.get('click', 0)}\n"
    text += f"• Сборщик: уровень {upgrades.get('collector', 0)}\n"
    text += f"• Золотых бананов куплено: {upgrades.get('gold', 0)}\n"
    return text

def shop_text(user: Dict) -> str:
    upgrades = user.get("upgrades", {})
    inventory = user.get("inventory", {})
    click_level = upgrades.get("click", 0)
    collector_level = upgrades.get("collector", 0)
    gold_level = upgrades.get("gold", 0)
    click_cost = cost_for_upgrade("click", click_level)
    collector_cost = cost_for_upgrade("collector", collector_level)
    gold_cost = cost_for_upgrade("gold", gold_level)
    gold_in_inventory = inventory.get("gold_banana", 0)
    return (
        f"🛒 Магазин улучшений\n\n"
        f"💰 Баланс: {int(user['bananas'])} 🍌\n\n"
        f"1️⃣ Улучшить клик (уровень {click_level}) → +1 банан за клик\n"
        f"💵 Стоимость: {click_cost} 🍌\n\n"
        f"2️⃣ Улучшить сборщик (уровень {collector_level}) → +1 банан/сек\n"
        f"💵 Стоимость: {collector_cost} 🍌\n\n"
        f"3️⃣ Купить Золотой Банан ✨ (куплено: {gold_level}, в инвентаре: {gold_in_inventory})\n"
        f"💵 Стоимость: {gold_cost} 🍌\n"
        f"⚡ Эффект: x2 к кликам на {GOLD_DURATION} секунд\n"
        f"📦 Добавляется в инвентарь, а не активируется сразу!"
    )

def inventory_text(user: Dict) -> str:
    inventory = user.get("inventory", {})
    if not inventory:
        return "🎒 Инвентарь пуст\n\nКупи Золотые Бананы в магазине или получи их за перерождения!"
    text = "🎒 Твой инвентарь:\n\n"
    gold_bananas = inventory.get("gold_banana", 0)
    if gold_bananas > 0:
        text += f"✨ Золотой Банан: {gold_bananas} шт.\n"
        text += f"   ⚡ Эффект: x2 к кликам на 5 минут\n"
        text += f"   💡 Использование: +5 минут за каждый банан\n\n"
        if has_active_gold(user):
            remaining = int(user.get("gold_expires", 0) - time.time())
            text += f"   ⏰ Активно: {remaining//60} мин {remaining%60} сек\n\n"
    text += "\n📦 Используй предметы для усиления!"
    return text

def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Улучшить клик", callback_data="buy_click")],
        [InlineKeyboardButton(text="⚙️ Улучшить сборщик", callback_data="buy_collector")],
        [InlineKeyboardButton(text="✨ Купить золотой банан", callback_data="buy_gold")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="⬅ Назад в меню", callback_data="back_to_main")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click"),
         InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])

def inventory_keyboard(user: Dict):
    inventory = user.get("inventory", {})
    gold_bananas = inventory.get("gold_banana", 0)
    buttons = []
    if gold_bananas > 0:
        buttons.append([InlineKeyboardButton(
            text=f"✨ Использовать Золотой Банан (есть: {gold_bananas})", 
            callback_data="use_gold_banana"
        )])
    buttons.append([InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")])
    buttons.append([InlineKeyboardButton(text="⬅ Назад в меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Выдать бананы", callback_data="admin_give_bananas")],
        [InlineKeyboardButton(text="✨ Запустить ивент", callback_data="admin_start_event")],
        [InlineKeyboardButton(text="👥 Новые регистрации", callback_data="admin_new_users")],
        [InlineKeyboardButton(text="🔄 Сбросить данные", callback_data="admin_reset_data")]
    ])

def admin_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад в админ-панель", callback_data="admin_back")]
    ])

def events_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_data in AVAILABLE_EVENTS.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=event_data["name"], 
                callback_data=f"admin_event_{event_id}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back")
    ])
    return keyboard

def login_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти в аккаунт", callback_data="login")],
        [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="register")]
    ])

# --------------------- РЕГИСТРАЦИЯ ---------------------

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    telegram_username = message.from_user.username or "unknown"
    user = db.get_user(user_id)
    if user:
        db.update_user(user_id, telegram_username=telegram_username)
        ensure_and_update_offline(user_id)
        await message.answer(f"👋 С возвращением, {user.get('nickname', 'друг')}!\nНакликай себе бананы!", reply_markup=main_menu_keyboard())
    else:
        await message.answer(
            "👋 Добро пожаловать в Banana Bot!\n\n"
            "Для игры необходимо иметь аккаунт. Выберите действие:",
            reply_markup=login_keyboard()
        )

# --------------------- CALLBACKS ---------------------
# Основные кнопки: click, shop, inventory, rebirth, profile, back_to_main

@router.callback_query(F.data.in_(["click", "profile", "shop", "inventory", "back_to_main", "rebirth"]))
async def handle_main_buttons(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Вы не авторизованы!", show_alert=True)
        return
    user = ensure_and_update_offline(user_id)
    data = callback.data

    if data == "click":
        per_click = effective_per_click(user)
        new_bananas = user["bananas"] + per_click
        db.update_user(user_id, bananas=new_bananas, last_update=time.time())
        user = db.get_user(user_id)
        text = f"🍌 Клик! +{per_click}\n\nВсего: {int(user['bananas'])} 🍌\nЗа клик: {effective_per_click(user)}\nПассив: {user['per_second']}/сек"
        await callback.message.edit_text(text, reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    elif data == "profile":
        await callback.message.edit_text(profile_text(user), reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    elif data == "shop":
        await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())
        await callback.answer()
        return

    elif data == "inventory":
        await callback.message.edit_text(inventory_text(user), reply_markup=inventory_keyboard(user))
        await callback.answer()
        return

    elif data == "back_to_main":
        await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    elif data == "rebirth":
        # тут перерождение
        await callback.message.edit_text("🔁 Перерождение\n\nВы уверены, что хотите переродиться?", 
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                             [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_rebirth")],
                                             [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
                                         ]))
        await callback.answer()
        return

# --------------------- Покупки и инвентарь ---------------------

@router.callback_query(F.data.in_(["buy_click", "buy_collector", "buy_gold", "use_gold_banana"]))
async def handle_shop_actions(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Вы не авторизованы!", show_alert=True)
        return
    user = ensure_and_update_offline(user_id)
    data = callback.data

    if data == "buy_click":
        click_level = user.get("upgrades", {}).get("click", 0)
        cost = cost_for_upgrade("click", click_level)
        if user["bananas"] >= cost:
            db.update_user(user_id, bananas=user["bananas"] - cost)
            upgrades = user.get("upgrades", {})
            upgrades["click"] = click_level + 1
            db.update_user(user_id, upgrades=upgrades)
            await callback.answer(f"✅ Клик улучшен до уровня {click_level + 1}!", show_alert=True)
        else:
            await callback.answer("❌ Недостаточно бананов!", show_alert=True)

    elif data == "buy_collector":
        collector_level = user.get("upgrades", {}).get("collector", 0)
        cost = cost_for_upgrade("collector", collector_level)
        if user["bananas"] >= cost:
            db.update_user(user_id, bananas=user["bananas"] - cost)
            upgrades = user.get("upgrades", {})
            upgrades["collector"] = collector_level + 1
            db.update_user(user_id, upgrades=upgrades)
            await callback.answer(f"✅ Сборщик улучшен до уровня {collector_level + 1}!", show_alert=True)
        else:
            await callback.answer("❌ Недостаточно бананов!", show_alert=True)

    elif data == "buy_gold":
        gold_level = user.get("upgrades", {}).get("gold", 0)
        cost = cost_for_upgrade("gold", gold_level)
        if user["bananas"] >= cost:
            db.update_user(user_id, bananas=user["bananas"] - cost)
            upgrades = user.get("upgrades", {})
            upgrades["gold"] = gold_level + 1
            db.update_user(user_id, upgrades=upgrades)
            inventory = user.get("inventory", {})
            inventory["gold_banana"] = inventory.get("gold_banana", 0) + 1
            db.update_user(user_id, inventory=inventory)
            await callback.answer(f"✅ Куплен Золотой Банан!", show_alert=True)
        else:
            await callback.answer("❌ Недостаточно бананов!", show_alert=True)

    elif data == "use_gold_banana":
        inventory = user.get("inventory", {})
        if inventory.get("gold_banana", 0) > 0:
            inventory["gold_banana"] -= 1
            current_expires = max(user.get("gold_expires", 0), time.time())
            new_expires = current_expires + GOLD_DURATION
            db.update_user(user_id, inventory=inventory, gold_expires=new_expires)
            await callback.answer("✅ Золотой банан активирован!", show_alert=True)
        else:
            await callback.answer("❌ Нет золотых бананов в инвентаре!", show_alert=True)

    # Обновляем текст после действия
    user = db.get_user(user_id)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard() if data != "use_gold_banana" else inventory_keyboard(user))
