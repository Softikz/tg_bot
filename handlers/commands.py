# handlers/commands.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time
import asyncio
import logging
from typing import Dict

from storage.db import DB
from game.logic import (
    apply_offline_gain,
    cost_for_upgrade,
    effective_per_click,
    GOLD_DURATION,
    has_active_gold,
    calculate_per_click,
    calculate_per_second
)

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
        f"🖱 За клик: {effective_per_click(user)} (база: {user['per_click']})\n"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
    )
    if has_active_gold(user):
        remaining = int(user.get("gold_expires", 0) - time.time())
        text += f"✨ Золотой банан активен! ({remaining} сек)\n"
    text += f"🔁 Перерождений: {user.get('rebirths', 0)}\n"
    
    # Показываем улучшения
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


def shop_keyboard(user: Dict):
    upgrades = user.get("upgrades", {})
    
    click_level = upgrades.get("click", 0)
    collector_level = upgrades.get("collector", 0)
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🖱 Улучшить клик (ур. {click_level})", callback_data="buy_click")],
        [InlineKeyboardButton(text=f"⚙️ Улучшить сборщик (ур. {collector_level})", callback_data="buy_collector")],
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


# === Команды ===

@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    ensure_and_update_offline(user_id, username)
    await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=main_menu_keyboard())


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


@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(profile_text(user), reply_markup=main_menu_keyboard())


@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(shop_text(user), reply_markup=shop_keyboard(user))


# === Callback кнопки ===

@router.callback_query(F.data == "click")
async def cb_click(query: CallbackQuery):
    await query.answer()  # обязательно отвечаем на callback
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    per_click = effective_per_click(user)
    
    # Добавляем бананы за клик
    new_bananas = user['bananas'] + per_click
    db.update_user(query.from_user.id, bananas=new_bananas, last_update=time.time())
    
    user = db.get_user(query.from_user.id)
    text = (
        f"🍌 Клик! +{per_click}\n\n"
        f"Всего: {int(user['bananas'])} 🍌\n"
        f"За клик: {effective_per_click(user)} (база: {user['per_click']})\n"
        f"Пассив: {user['per_second']}/сек\n"
    )
    if has_active_gold(user):
        remaining = int(user.get("gold_expires", 0) - time.time())
        text += f"✨ Активен Золотой Банан (2×) - {remaining} сек\n"
    
    await query.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "shop")
async def cb_shop(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


@router.callback_query(F.data == "profile")
async def cb_profile(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(profile_text(user), reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text("🏠 Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.in_({"buy_click", "buy_collector", "buy_gold"}))
async def cb_buy_upgrade(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    upgrades = user.get("upgrades", {}) or {}
    kind = query.data.replace("buy_", "")
    level = upgrades.get(kind, 0)

    try:
        cost = cost_for_upgrade(kind, level)
    except Exception as e:
        await query.answer(f"Ошибка расчёта стоимости: {e}", show_alert=True)
        return

    if user["bananas"] < cost:
        await query.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    # Вычитаем стоимость
    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades[kind] = level + 1

    # Обновляем характеристики в зависимости от типа улучшения
    if kind == "click":
        new_per_click = calculate_per_click(new_upgrades)
        db.update_user(
            query.from_user.id, 
            bananas=new_bananas, 
            per_click=new_per_click, 
            upgrades=new_upgrades
        )
        await query.answer(f"✅ Улучшение клика куплено! Теперь уровень {level + 1}", show_alert=True)
        
    elif kind == "collector":
        new_per_second = calculate_per_second(new_upgrades)
        db.update_user(
            query.from_user.id, 
            bananas=new_bananas, 
            per_second=new_per_second, 
            upgrades=new_upgrades
        )
        await query.answer(f"✅ Улучшение сборщика куплено! Теперь уровень {level + 1}", show_alert=True)
        
    elif kind == "gold":
        # Активируем золотой банан
        gold_expires = time.time() + GOLD_DURATION
        db.update_user(
            query.from_user.id, 
            bananas=new_bananas, 
            gold_expires=gold_expires, 
            upgrades=new_upgrades
        )
        await query.answer(f"✅ Золотой банан активирован! +x2 к кликам на {GOLD_DURATION} секунд", show_alert=True)

    # Обновляем сообщение магазина
    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


# --- Перерождение (rebirth) ---
REQUIREMENTS = [
    {"bananas": 500, "gold": 0},
    {"bananas": 1000, "gold": 1},
]

@router.callback_query(F.data == "rebirth")
async def rebirth_prompt(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    req = REQUIREMENTS[min(rebirth_count, len(REQUIREMENTS)-1)]
    collected = user["bananas"]
    total_needed = req["bananas"]
    progress_percent = min(100, int(collected / total_needed * 100)) if total_needed > 0 else 100
    filled = int(progress_percent / 10)
    empty = 10 - filled
    bar = "🟩"*filled + "⬜"*empty

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Переродиться", callback_data="confirm_rebirth")
    builder.button(text="⬅ Назад", callback_data="back_to_main")

    await query.message.edit_text(
        f"🔁 Перерождение\n\n"
        f"Текущий уровень: {rebirth_count}\n"
        f"Собрано бананов: {int(collected)}/{total_needed}\n"
        f"{bar} {progress_percent}%\n\n"
        f"Требуется золотых бананов: {req.get('gold',0)}\n\n"
        f"⚠️ При перерождении весь прогресс сбрасывается, но вы получаете бонусы!",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "confirm_rebirth")
async def confirm_rebirth(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    req = REQUIREMENTS[min(rebirth_count, len(REQUIREMENTS)-1)]

    if user["bananas"] < req["bananas"] or user.get("upgrades", {}).get("gold", 0) < req.get("gold", 0):
        await query.answer("⚠️ Недостаточно бананов или золотых бананов для перерождения.", show_alert=True)
        return

    # Сбрасываем прогресс, но увеличиваем счетчик перерождений
    db.update_user(
        query.from_user.id, 
        bananas=0, 
        per_click=1, 
        per_second=0, 
        upgrades={},
        rebirths=rebirth_count + 1
    )

    await query.message.edit_text(
        f"🌟 Вы переродились! Уровень перерождения: {rebirth_count + 1}\n\n"
        f"Прогресс сброшен, но вы стали сильнее!",
        reply_markup=main_menu_keyboard()
    )


# === DEBUG: ловим все неизвестные callback'и ===
@router.callback_query()
async def _debug_unhandled_callback(query: CallbackQuery):
    try:
        await query.answer()  # отвечаем, чтобы спиннер исчез
    except Exception:
        pass
    log.info("⚠️ Unhandled callback_query received. from=%s data=%s message_id=%s",
             query.from_user.id, query.data, getattr(query.message, "message_id", None))


@router.message()
async def _debug_unhandled_message(message: types.Message):
    log.info("⚠️ Unhandled message: from=%s text=%s", message.from_user.id, message.text)
