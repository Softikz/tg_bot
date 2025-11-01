# handlers/commands.py
import time
import logging
import asyncio
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
ADMIN_ID = 789273255  # Ваш ID
log = logging.getLogger(__name__)

# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_bananas_amount = State()
    waiting_for_event_type = State()
    waiting_for_event_duration = State()

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_password = State()

# Список доступных ивентов
AVAILABLE_EVENTS = {
    "event_update_2x": {"name": "🎉 Ивент в честь обновления x2", "multiplier": 2.0},
    "event_update_3x": {"name": "🎊 Ивент в честь обновления x3", "multiplier": 3.0},
    "event_update_5x": {"name": "🚀 Ивент в честь обновления x5", "multiplier": 5.0},
    "event_weekend_2x": {"name": "🎯 Выходной ивент x2", "multiplier": 2.0},
    "event_special_4x": {"name": "💎 Специальный ивент x4", "multiplier": 4.0}
}

def ensure_and_update_offline(user_id: int, username: str):
    db.create_user_if_not_exists(user_id, username)
    user = db.get_user(user_id)
    if not user:
        raise RuntimeError("Не удалось получить пользователя из БД")
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
    text = (
        f"👤 Профиль @{user['username']}\n\n"
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
        
        # Показываем текущее активное время если есть
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

# ========== РЕГИСТРАЦИЯ ==========

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # Проверяем, есть ли пользователь в базе
    user = db.get_user(user_id)
    
    if not user:
        # Если пользователя нет, начинаем регистрацию
        await message.answer(
            "👋 Добро пожаловать! Для доступа к боту необходимо зарегистрироваться.\n\n"
            "🔐 Введите пароль для регистрации:"
        )
        await state.set_state(RegistrationStates.waiting_for_password)
    else:
        # Если пользователь уже зарегистрирован
        ensure_and_update_offline(user_id, username)
        await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=main_menu_keyboard())

@router.message(RegistrationStates.waiting_for_password)
async def process_registration_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    
    # Проверяем пароль (можно сделать более сложную логику)
    if password == "banana123":  # Пароль для регистрации
        user_id = message.from_user.id
        username = message.from_user.username or "unknown"
        
        # Создаем пользователя
        db.create_user_if_not_exists(user_id, username)
        
        # Уведомляем админа о новой регистрации
        try:
            from main import bot
            await bot.send_message(
                ADMIN_ID,
                f"🆕 Новая регистрация!\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"🕒 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass
        
        await message.answer(
            "✅ Регистрация успешна! Добро пожаловать в Banana Bot!\n\n"
            "Теперь ты можешь кликать бананы, улучшать свои возможности и участвовать в ивентах!",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз:")

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(profile_text(user), reply_markup=main_menu_keyboard())

@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(shop_text(user), reply_markup=shop_keyboard())

@router.message(Command("inventory"))
async def inventory_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(inventory_text(user), reply_markup=inventory_keyboard(user))

# ========== АДМИН КОМАНДЫ ==========

@router.message(Command("admin"))
async def admin_command(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем права администратора
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    # Проверяем пароль
    if len(message.text.split()) < 2:
        await message.answer("❌ Использование: /admin <пароль>")
        return
    
    password = message.text.split()[1]
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль администратора!")
        return
    
    await message.answer("🛠️ Панель администратора:", reply_markup=admin_keyboard())

# ========== CALLBACK ОБРАБОТЧИКИ ==========

@router.callback_query(F.data == "click")
async def handle_click(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    per_click = effective_per_click(user)
    
    new_bananas = user['bananas'] + per_click
    db.update_user(callback.from_user.id, bananas=new_bananas, last_update=time.time())
    
    user = db.get_user(callback.from_user.id)
    
    text = (
        f"🍌 Клик! +{per_click}\n\n"
        f"Всего: {int(user['bananas'])} 🍌\n"
        f"За клик: {effective_per_click(user)}\n"
        f"Пассив: {user['per_second']}/сек\n"
    )
    
    boosts = []
    if has_active_gold(user):
        remaining = int(user.get("gold_expires", 0) - time.time())
        boosts.append(f"✨ Золотой банан (2×)")
    
    if has_active_event(user):
        remaining = int(user.get("event_expires", 0) - time.time())
        multiplier = user.get("event_multiplier", 1.0)
        event_type = user.get("event_type", "")
        boosts.append(f"🎯 {event_type} ({multiplier}×)")
    
    if boosts:
        text += "⚡ " + " + ".join(boosts) + "\n"
    
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "profile")
async def handle_profile(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(profile_text(user), reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "shop")
async def handle_shop(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())

@router.callback_query(F.data == "inventory")
async def handle_inventory(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(inventory_text(user), reply_markup=inventory_keyboard(user))

@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "use_gold_banana")
async def handle_use_gold_banana(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    
    # Используем один золотой банан из инвентаря
    if db.use_from_inventory(callback.from_user.id, "gold_banana", 1):
        # Активируем золотой банан - увеличиваем время
        current_expires = user.get("gold_expires", 0)
        current_time = time.time()
        
        # Если текущее время истекло, начинаем с текущего момента
        if current_expires < current_time:
            new_expires = current_time + GOLD_DURATION
        else:
            # Иначе добавляем к существующему времени
            new_expires = current_expires + GOLD_DURATION
        
        db.update_user(callback.from_user.id, gold_expires=new_expires)
        
        remaining = db.get_inventory(callback.from_user.id).get("gold_banana", 0)
        remaining_time = int(new_expires - current_time)
        
        await callback.answer(
            f"✅ Золотой банан активирован! +5 минут буста.\n"
            f"⏰ Общее время: {remaining_time//60} мин {remaining_time%60} сек\n"
            f"📦 Осталось в инвентаре: {remaining}", 
            show_alert=True
        )
        
        user = db.get_user(callback.from_user.id)
        await callback.message.edit_text(inventory_text(user), reply_markup=inventory_keyboard(user))
    else:
        await callback.answer("❌ Нет золотых бананов в инвентаре!", show_alert=True)

# Покупки улучшений
@router.callback_query(F.data == "buy_click")
async def handle_buy_click(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    upgrades = user.get("upgrades", {}) or {}
    level = upgrades.get("click", 0)
    cost = cost_for_upgrade("click", level)

    if user["bananas"] < cost:
        await callback.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades["click"] = level + 1
    new_per_click = calculate_per_click(new_upgrades)

    db.update_user(
        callback.from_user.id, 
        bananas=new_bananas, 
        per_click=new_per_click, 
        upgrades=new_upgrades
    )
    
    next_level = level + 1
    next_cost = cost_for_upgrade("click", next_level)
    
    await callback.answer(f"✅ Улучшение клика куплено! Уровень {next_level}. Следующее: {next_cost} 🍌", show_alert=True)
    
    user = db.get_user(callback.from_user.id)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())

@router.callback_query(F.data == "buy_collector")
async def handle_buy_collector(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    upgrades = user.get("upgrades", {}) or {}
    level = upgrades.get("collector", 0)
    cost = cost_for_upgrade("collector", level)

    if user["bananas"] < cost:
        await callback.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades["collector"] = level + 1
    new_per_second = calculate_per_second(new_upgrades)

    db.update_user(
        callback.from_user.id, 
        bananas=new_bananas, 
        per_second=new_per_second, 
        upgrades=new_upgrades
    )
    
    await callback.answer(f"✅ Улучшение сборщика куплено! Теперь уровень {level + 1}", show_alert=True)
    
    user = db.get_user(callback.from_user.id)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())

@router.callback_query(F.data == "buy_gold")
async def handle_buy_gold(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    upgrades = user.get("upgrades", {}) or {}
    level = upgrades.get("gold", 0)
    cost = cost_for_upgrade("gold", level)

    if user["bananas"] < cost:
        await callback.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades["gold"] = level + 1
    
    # Добавляем золотой банан в инвентарь вместо немедленной активации
    inventory = user.get("inventory", {})
    inventory["gold_banana"] = inventory.get("gold_banana", 0) + 1
    
    db.update_user(
        callback.from_user.id, 
        bananas=new_bananas, 
        upgrades=new_upgrades,
        inventory=inventory
    )
    
    await callback.answer(f"✅ Золотой банан куплен! Добавлен в инвентарь. Осталось: {inventory['gold_banana']}", show_alert=True)
    
    user = db.get_user(callback.from_user.id)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())

# ========== ПЕРЕРОЖДЕНИЕ ==========

@router.callback_query(F.data == "rebirth")
async def handle_rebirth(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    current_bananas = user["bananas"]
    requirement = get_rebirth_requirement(rebirth_count)
    
    progress_bar = create_progress_bar(current_bananas, requirement)
    reward = get_rebirth_reward(rebirth_count)
    
    text = (
        f"🌌 Перерождение\n\n"
        f"🔁 Перерождений всего: {rebirth_count}\n"
        f"🍌 Твои бананы: {current_bananas}/{requirement}\n"
        f"{progress_bar}\n\n"
        f"🎁 Награда за перерождение:\n{reward}\n\n"
        f"⚠️ При перерождении весь прогресс сбрасывается!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    if current_bananas >= requirement:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🚀 ПЕРЕРОДИТЬСЯ", callback_data="confirm_rebirth")])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "confirm_rebirth")
async def handle_confirm_rebirth(callback: CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    requirement = get_rebirth_requirement(rebirth_count)
    
    if user["bananas"] < requirement:
        await callback.answer("❌ Недостаточно бананов для перерождения!", show_alert=True)
        return
    
    # Анимация перерождения
    animation_messages = [
        "🌠 Запускаем перерождение...",
        "💫 Собираем звёздную пыль...",
        "☄️ Призываем метеориты...",
        "🌟 Поглощаем энергию вселенной...",
        "🚀 ПЕРЕРОЖДЕНИЕ!"
    ]
    
    for i, message in enumerate(animation_messages):
        stars = "✨" * (i + 1)
        meteors = "☄️" * (i + 1)
        await callback.message.edit_text(f"{stars}\n{message}\n{meteors}")
        await asyncio.sleep(1)
    
    # Награды за перерождение
    rewards = {
        0: {"gold_banana": 1},
        1: {"gold_banana": 2},
        2: {"gold_banana": 3},
        3: {"gold_banana": 5},
        4: {"gold_banana": 8}
    }
    
    reward = rewards.get(rebirth_count, {"gold_banana": 10})
    
    # Добавляем награды в инвентарь
    inventory = user.get("inventory", {})
    for item, quantity in reward.items():
        inventory[item] = inventory.get(item, 0) + quantity
    
    # Сбрасываем прогресс и увеличиваем счетчик перерождений
    # НЕ сбрасываем инвентарь и rebirths!
    db.update_user(
        callback.from_user.id, 
        bananas=0, 
        per_click=1, 
        per_second=0, 
        upgrades={},
        rebirths=rebirth_count + 1,
        inventory=inventory,
        gold_expires=0  # Сбрасываем активные бусты
    )
    
    # Финальное сообщение
    reward_text = ""
    for item, quantity in reward.items():
        if item == "gold_banana":
            reward_text += f"✨ Золотых Бананов: +{quantity}\n"
    
    await callback.message.edit_text(
        f"🎉 Перерождение завершено!\n\n"
        f"🔁 Уровень перерождения: {rebirth_count + 1}\n\n"
        f"🎁 Полученные награды:\n{reward_text}\n"
        f"💫 Ты стал сильнее! Прогресс сброшен, но награды остались с тобой!",
        reply_markup=main_menu_keyboard()
    )

# ========== АДМИН ОБРАБОТЧИКИ ==========

@router.callback_query(F.data.startswith("admin_"))
async def handle_admin_commands(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Проверяем права администратора
    if user_id != ADMIN_ID:
        await callback.answer("❌ У вас нет прав администратора!", show_alert=True)
        return
    
    action = callback.data
    
    if action == "admin_stats":
        users = db.all_users()
        total_users = len(users)
        total_bananas = sum(user.get("bananas", 0) for user in users)
        total_rebirths = sum(user.get("rebirths", 0) for user in users)
        
        # Новые пользователи (за последние 24 часа)
        new_users = 0
        for user in users:
            if user.get("last_update", 0) > time.time() - 86400:
                new_users += 1
        
        stats_text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"🆕 Новых за 24ч: {new_users}\n"
            f"🍌 Всего бананов: {total_bananas}\n"
            f"🔁 Всего перерождений: {total_rebirths}\n"
            f"🕒 Время сервера: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await callback.message.edit_text(stats_text, reply_markup=admin_back_keyboard())
        await callback.answer()
        
    elif action == "admin_give_bananas":
        await callback.message.edit_text(
            "🎁 Выдача бананов\n\n"
            "Выберите способ выдачи:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 Конкретному пользователю", callback_data="admin_give_single")],
                [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="admin_give_all")],
                [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back")]
            ])
        )
        await callback.answer()
        
    elif action == "admin_give_single":
        await callback.message.edit_text(
            "👤 Выдача бананов пользователю\n\n"
            "Введите @username пользователя (например, @username):"
        )
        await state.set_state(AdminStates.waiting_for_username)
        await callback.answer()
        
    elif action == "admin_give_all":
        await callback.message.edit_text(
            "👥 Выдача бананов всем пользователям\n\n"
            "Введите количество бананов для выдачи всем:"
        )
        await state.set_state(AdminStates.waiting_for_bananas_amount)
        await state.update_data(give_all=True)
        await callback.answer()
        
    elif action == "admin_start_event":
        await callback.message.edit_text(
            "✨ Запуск ивента\n\n"
            "Выберите тип ивента:",
            reply_markup=events_keyboard()
        )
        await callback.answer()
        
    elif action == "admin_new_users":
        users = db.all_users()
        # Сортируем по времени регистрации (последние сначала)
        users.sort(key=lambda x: x.get("last_update", 0), reverse=True)
        
        new_users_text = "👥 Последние регистрации:\n\n"
        count = 0
        for user in users[:10]:  # Показываем последние 10
            username = user.get("username", "unknown")
            user_id = user.get("user_id")
            reg_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(user.get("last_update", time.time())))
            new_users_text += f"👤 @{username} (ID: {user_id})\n🕒 {reg_time}\n\n"
            count += 1
        
        if count == 0:
            new_users_text = "❌ Нет зарегистрированных пользователей"
            
        await callback.message.edit_text(new_users_text, reply_markup=admin_back_keyboard())
        await callback.answer()
        
    elif action == "admin_reset_data":
        # Опасно! Сброс всех данных
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ДА, сбросить все", callback_data="admin_confirm_reset")],
            [InlineKeyboardButton(text="✅ Нет, отмена", callback_data="admin_back")]
        ])
        await callback.message.edit_text(
            "⚠️ ВНИМАНИЕ! Это сбросит ВСЕ данные всех пользователей!\n\n"
            "Вы уверены? Это действие нельзя отменить!",
            reply_markup=keyboard
        )
        await callback.answer()
        
    elif action == "admin_back":
        await callback.message.edit_text("🛠️ Панель администратора:", reply_markup=admin_keyboard())
        await callback.answer()
        
    elif action.startswith("admin_event_"):
        event_id = action.replace("admin_event_", "")
        event_data = AVAILABLE_EVENTS.get(event_id)
        
        if event_data:
            await callback.message.edit_text(
                f"🎯 Запуск ивента: {event_data['name']}\n\n"
                f"Множитель: x{event_data['multiplier']}\n\n"
                f"Введите длительность ивента в формате 'часы:минуты' (например, 2:30 для 2 часов 30 минут):"
            )
            await state.set_state(AdminStates.waiting_for_event_duration)
            await state.update_data(event_id=event_id, event_data=event_data)
            await callback.answer()

@router.callback_query(F.data == "admin_confirm_reset")
async def handle_admin_confirm_reset(callback: CallbackQuery):
    # Сбрасываем всех пользователей
    users = db.all_users()
    for user in users:
        db.update_user(
            user["user_id"],
            bananas=0,
            per_click=1,
            per_second=0,
            upgrades={},
            rebirths=0,
            inventory={},
            gold_expires=0
        )
    
    await callback.message.edit_text(
        "✅ Все данные пользователей сброшены!",
        reply_markup=admin_keyboard()
    )
    await callback.answer("Данные сброшены!", show_alert=True)

# ========== АДМИН STATES ОБРАБОТЧИКИ ==========

@router.message(AdminStates.waiting_for_username)
async def process_admin_username(message: types.Message, state: FSMContext):
    username = message.text.strip().replace('@', '')  # Убираем @ если есть
    
    # Ищем пользователя по username
    users = db.all_users()
    target_user = None
    for user in users:
        if user.get("username", "").lower() == username.lower():
            target_user = user
            break
    
    if not target_user:
        await message.answer("❌ Пользователь с таким username не найден. Попробуйте еще раз:")
        return
    
    await state.update_data(target_user_id=target_user["user_id"], target_username=target_user["username"])
    await message.answer(f"👤 Найден пользователь: @{target_user['username']}\n\nВведите количество бананов для выдачи:")
    await state.set_state(AdminStates.waiting_for_bananas_amount)

@router.message(AdminStates.waiting_for_bananas_amount)
async def process_admin_bananas_amount(message: types.Message, state: FSMContext):
    try:
        bananas = int(message.text)
        if bananas <= 0:
            await message.answer("❌ Количество бананов должно быть положительным. Попробуйте еще раз:")
            return
            
        data = await state.get_data()
        
        if data.get("give_all"):
            # Выдаем бананы всем пользователям
            users = db.all_users()
            for user in users:
                current_bananas = user.get("bananas", 0)
                db.update_user(user["user_id"], bananas=current_bananas + bananas)
            
            await message.answer(
                f"✅ Успешно выдано {bananas} 🍌 всем {len(users)} пользователям!",
                reply_markup=admin_keyboard()
            )
        else:
            # Выдаем бананы конкретному пользователю
            target_user_id = data["target_user_id"]
            target_username = data["target_username"]
            
            user = db.get_user(target_user_id)
            current_bananas = user.get("bananas", 0)
            db.update_user(target_user_id, bananas=current_bananas + bananas)
            
            await message.answer(
                f"✅ Успешно выдано {bananas} 🍌 пользователю @{target_username}!",
                reply_markup=admin_keyboard()
            )
            
            # Уведомляем пользователя
            try:
                from main import bot
                await bot.send_message(
                    target_user_id,
                    f"🎁 Администратор выдал вам {bananas} 🍌!\n\n"
                    f"Теперь у вас: {current_bananas + bananas} бананов"
                )
            except:
                pass
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат числа. Введите целое число:")

@router.message(AdminStates.waiting_for_event_duration)
async def process_admin_event_duration(message: types.Message, state: FSMContext):
    try:
        duration_str = message.text.strip()
        duration_seconds = parse_event_duration(duration_str)
        
        data = await state.get_data()
        event_id = data["event_id"]
        event_data = data["event_data"]
        
        # Запускаем ивент для всех пользователей
        db.start_event_for_all_users(
            event_data["name"],
            event_data["multiplier"],
            duration_seconds
        )
        
        # Уведомляем всех пользователей
        users = db.all_users()
        notified = 0
        from main import bot
        
        for user in users:
            try:
                await bot.send_message(
                    user["user_id"],
                    f"🎉 {event_data['name']}!\n\n"
                    f"⚡ Множитель бананов: x{event_data['multiplier']}\n"
                    f"⏰ Длительность: {duration_str}\n\n"
                    f"Успей получить максимум бананов! 🍌"
                )
                notified += 1
            except:
                continue
        
        await message.answer(
            f"✅ Ивент '{event_data['name']}' запущен!\n\n"
            f"📊 Статистика:\n"
            f"• Множитель: x{event_data['multiplier']}\n"
            f"• Длительность: {duration_str}\n"
            f"• Уведомлено пользователей: {notified}/{len(users)}",
            reply_markup=admin_keyboard()
        )
        
        await state.clear()
        
    except ValueError as e:
        await message.answer(f"❌ {str(e)}\n\nПопробуйте еще раз в формате 'часы:минуты':")
