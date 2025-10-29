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
    has_active_gold
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
        f"🍌 Бананы: {user['bananas']}\n"
        f"🖱 За клик: {user['per_click']}\n"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
    )
    if has_active_gold(user):
        text += "✨ Золотой банан активен!\n"
    text += f"🔁 Перерождений: {user.get('rebirths', 0)}\n"
    return text


def shop_text(user: Dict) -> str:
    return (
        f"🛒 Магазин улучшений\n\n"
        f"💰 Баланс: {user['bananas']} 🍌\n"
        f"1️⃣ Улучшить клик (+1) — {cost_for_upgrade('click', user['upgrades'].get('click', 0))} 🍌\n"
        f"2️⃣ Улучшить пассив (+1/сек) — {cost_for_upgrade('collector', user['upgrades'].get('collector', 0))} 🍌\n"
        f"3️⃣ Купить Золотой Банан ✨ — {cost_for_upgrade('gold', user['upgrades'].get('gold', 0))} 🍌\n"
    )


def shop_keyboard(user: Dict):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Улучшить клик", callback_data="buy_click")],
        [InlineKeyboardButton(text="⚙️ Улучшить сборщик", callback_data="buy_collector")],
        [InlineKeyboardButton(text="✨ Купить золотой банан", callback_data="buy_gold")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="profile")]
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click"),
         InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
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
    db.update_user(query.from_user.id, bananas=user['bananas'] + per_click, last_update=time.time())
    user = db.get_user(query.from_user.id)
    text = (
        f"🍌 Клик! +{per_click}\n\n"
        f"Всего: {user['bananas']} 🍌\n"
        f"За клик: {user['per_click']}\n"
        f"Пассив: {user['per_second']}/сек\n"
    )
    if has_active_gold(user):
        text += "✨ Активен Золотой Банан (2×)\n"
    await query.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "shop")
async def cb_shop(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


@router.callback_query(F.data.in_({"buy_click", "buy_collector", "buy_gold"}))
async def cb_buy_upgrade(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    upgrades = user.get("upgrades", {}) or {}
    kind = query.data.replace("buy_", "")
    level = upgrades.get(kind, 0)

    try:
        cost = cost_for_upgrade(kind, level)
    except Exception:
        await query.answer("Ошибка расчёта стоимости.", show_alert=True)
        return

    if user["bananas"] < cost:
        await query.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades[kind] = level + 1

    if kind == "click":
        db.update_user(query.from_user.id, bananas=new_bananas, per_click=user["per_click"] + 1, upgrades=new_upgrades)
    elif kind == "collector":
        db.update_user(query.from_user.id, bananas=new_bananas, per_second=user["per_second"] + 1, upgrades=new_upgrades)
    elif kind == "gold":
        db.update_user(query.from_user.id, bananas=new_bananas, gold_expires=time.time() + GOLD_DURATION, upgrades=new_upgrades)

    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


# --- Перерождение (rebirth) ---
REQUIREMENTS = [
    {"bananas": 500, "gold": 0},
    {"bananas": 1000, "gold": 1},
    # можно расширить
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
    builder.button(text="Переродиться", callback_data="confirm_rebirth")
    builder.button(text="⬅ Назад", callback_data="profile")

    await query.message.edit_text(
        f"🔁 Перерождение\n\n"
        f"Всего бананов собрано: {collected}/{total_needed}\n"
        f"{bar} {progress_percent}%\n\n"
        f"Требуется золотых бананов: {req.get('gold',0)}",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "confirm_rebirth")
async def confirm_rebirth(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    rebirth_count = user.get("rebirths", 0)
    req = REQUIREMENTS[min(rebirth_count, len(REQUIREMENTS)-1)]

    if user["bananas"] < req["bananas"] or user.get("upgrades", {}).get("gold", 0) < req.get("gold", 0):
        await query.message.answer("⚠️ Недостаточно бананов или золотых бананов для перерождения.")
        return

    new_upgrades = user.get("upgrades", {}).copy()
    if req.get("gold", 0) > 0:
        new_upgrades["gold"] = max(0, new_upgrades.get("gold", 0) - req["gold"])

    db.update_user(query.from_user.id, bananas=0, per_click=1, per_second=0, upgrades=new_upgrades)
    db.update_user(query.from_user.id, rebirths=rebirth_count + 1)

    await query.message.answer("🌟 Вы переродились! Прогресс сброшен.")


# === DEBUG: ловим все неизвестные callback'и и сообщения ===
@router.callback_query()
async def _debug_unhandled_callback(query: CallbackQuery):
    try:
        await query.answer()  # отвечаем, чтобы спиннер исчез
    except Exception:
        pass
    log.info("⚠️ Unhandled callback_query received. from=%s data=%s message_id=%s",
             query.from_user.id, query.data, getattr(query.message, "message_id", None))
    # не делаем show_alert по умолчанию, просто логируем


@router.message()
async def _debug_unhandled_message(message: types.Message):
    log.info("⚠️ Unhandled message: from=%s text=%s", message.from_user.id, message.text)
