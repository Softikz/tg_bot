# handlers/commands.py
import time
import logging
from typing import Dict

from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

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
    parse_event_duration
)

# Создаем роутер
router = Router()
db = DB()
ADMIN_PASSWORD = "sm10082x3%"
log = logging.getLogger(__name__)


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


def profile_text(user: Dict) -> str:
    text = (
        f"👤 Профиль @{user['username']}\n\n"
        f"🍌 Бананы: {int(user['bananas'])}\n"
        f"🖱 За клик: {effective_per_click(user)}\n"  # УБРАЛ "(база: {user['per_click']})"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
    )
    
    # Информация об активных бустах
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
    
    text += f"🔁 Перерождений: {user.get('rebirths', 0)}\n"
    
    upgrades = user.get("upgrades", {})
    text += f"\n📊 Улучшения:\n"
    text += f"• Клик: уровень {upgrades.get('click', 0)}\n"
    text += f"• Сборщик: уровень {upgrades.get('collector', 0)}\n"
    text += f"• Золотых бананов куплено: {upgrades.get('gold', 0)}\n"
    
    return text


def shop_text(user: Dict) -> str:
    upgrades = user.get("upgrades", {})
    
    click_level = upgrades.get("click", 0)
    collector_level = upgrades.get("collector", 0)
    gold_level = upgrades.get("gold", 0)
    
    click_cost = cost_for_upgrade("click", click_level)
    collector_cost = cost_for_upgrade("collector", collector_level)
    gold_cost = cost_for_upgrade("gold", gold_level)
    
    return (
        f"🛒 Магазин улучшений\n\n"
        f"💰 Баланс: {int(user['bananas'])} 🍌\n\n"
        f"1️⃣ Улучшить клик (уровень {click_level}) → +1 банан за клик\n"
        f"💵 Стоимость: {click_cost} 🍌\n\n"
        f"2️⃣ Улучшить сборщик (уровень {collector_level}) → +1 банан/сек\n"
        f"💵 Стоимость: {collector_cost} 🍌\n\n"
        f"3️⃣ Купить Золотой Банан ✨ (куплено: {gold_level})\n"
        f"💵 Стоимость: {gold_cost} 🍌\n"
        f"⚡ Эффект: x2 к кликам на {GOLD_DURATION} секунд\n"
    )

def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Улучшить клик", callback_data="buy_click")],
        [InlineKeyboardButton(text="⚙️ Улучшить сборщик", callback_data="buy_collector")],
        [InlineKeyboardButton(text="✨ Купить золотой банан", callback_data="buy_gold")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")],
        [InlineKeyboardButton(text="⬅ Назад в меню", callback_data="back_to_main")]
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click"),
         InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])


# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========

@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    ensure_and_update_offline(user_id, username)
    await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=main_menu_keyboard())


@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(profile_text(user), reply_markup=main_menu_keyboard())


@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(shop_text(user), reply_markup=shop_keyboard())


@router.message(Command("admin"))
async def admin_command(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Использование: /admin <пароль> <кол-во бананов>")
        return

    _, password, amount = args
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль.")
        return

    try:
        amount = int(amount)
    except ValueError:
        await message.answer("⚠️ Количество должно быть числом.")
        return

    user = db.get_user(message.from_user.id)
    db.update_user(message.from_user.id, bananas=user["bananas"] + amount)
    await message.answer(f"✅ Добавлено {amount} 🍌\nБаланс: {user['bananas'] + amount} 🍌")


@router.message(Command("event"))
async def event_command(message: types.Message):
    """Админская команда для запуска ивентов"""
    args = message.text.split()
    if len(args) != 4:
        await message.answer(
            "⚠️ Использование: /event <пароль> <тип_ивента> <длительность>\n\n"
            "Примеры:\n"
            "/event sm10082x3% clickx5 1:30 - клики x5 на 1.5 часа\n"
            "/event sm10082x3% clickx3 0:45 - клики x3 на 45 минут\n"
            "/event sm10082x3% incomex2 2:00 - доход x2 на 2 часа"
        )
        return

    _, password, event_type, duration_str = args
    
    # Проверка пароля
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль.")
        return

    try:
        # Парсинг длительности
        duration_seconds = parse_event_duration(duration_str)
        
        # Парсинг типа ивента и множителя
        if 'x' in event_type:
            event_name, multiplier_str = event_type.split('x')
            multiplier = float(multiplier_str)
        else:
            event_name = event_type
            multiplier = 2.0  # значение по умолчанию
        
        # Запускаем ивент для всех пользователей
        db.start_event_for_all_users(event_type, multiplier, duration_seconds)
        
        # Форматируем время для ответа
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        
        time_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"
        
        await message.answer(
            f"🎉 Ивент запущен!\n\n"
            f"📊 Тип: {event_type}\n"
            f"⚡ Множитель: {multiplier}×\n"
            f"⏰ Длительность: {time_str}\n\n"
            f"Ивент автоматически завершится через указанное время."
        )
        
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {e}")
    except Exception as e:
        await message.answer(f"❌ Неизвестная ошибка: {e}")


# ========== ОБРАБОТЧИКИ CALLBACK КНОПОК ==========

@router.callback_query(F.data == "click")
async def handle_click(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    per_click = effective_per_click(user)
    
    new_bananas = user['bananas'] + per_click
    db.update_user(callback.from_user.id, bananas=new_bananas, last_update=time.time())
    
    user = db.get_user(callback.from_user.id)
    
    # Формируем текст с информацией о бустах
    text = (
        f"🍌 Клик! +{per_click}\n\n"
        f"Всего: {int(user['bananas'])} 🍌\n"
        f"За клик: {effective_per_click(user)}\n"  # УБРАЛ "(база: {user['per_click']})"
        f"Пассив: {user['per_second']}/сек\n"
    )
    
    # Добавляем информацию об активных бустах
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
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(profile_text(user), reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "shop")
async def handle_shop(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "buy_click")
async def handle_buy_click(callback: CallbackQuery):
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
    
    gold_expires = time.time() + GOLD_DURATION
    db.update_user(
        callback.from_user.id, 
        bananas=new_bananas, 
        gold_expires=gold_expires, 
        upgrades=new_upgrades
    )
    
    await callback.answer(f"✅ Золотой банан активирован! +x2 к кликам на {GOLD_DURATION} секунд", show_alert=True)
    
    user = db.get_user(callback.from_user.id)
    await callback.message.edit_text(shop_text(user), reply_markup=shop_keyboard())


@router.callback_query(F.data == "rebirth")
async def handle_rebirth(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Переродиться", callback_data="confirm_rebirth")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(
        f"🔁 Перерождение\n\n"
        f"Текущий уровень: {rebirth_count}\n"
        f"Собрано бананов: {int(user['bananas'])}\n\n"
        f"⚠️ При перерождении весь прогресс сбрасывается!",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "confirm_rebirth")
async def handle_confirm_rebirth(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    rebirth_count = user.get("rebirths", 0)

    db.update_user(
        callback.from_user.id, 
        bananas=0, 
        per_click=1, 
        per_second=0, 
        upgrades={},
        rebirths=rebirth_count + 1
    )

    await callback.message.edit_text(
        f"🌟 Вы переродились! Уровень перерождения: {rebirth_count + 1}\n\n"
        f"Прогресс сброшен, но вы стали сильнее!",
        reply_markup=main_menu_keyboard()
    )


# Обработчик для неизвестных callback'ов
@router.callback_query()
async def handle_unknown_callback(callback: CallbackQuery):
    log.warning(f"Необработанный callback: {callback.data} от пользователя {callback.from_user.id}")
    await callback.answer(f"Неизвестная команда: {callback.data}", show_alert=True)

