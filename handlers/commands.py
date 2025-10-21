# handlers/commands.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time
import asyncio
from typing import Dict

from storage.db import DB
from game.logic import (
    apply_offline_gain,
    cost_for_upgrade,
    effective_per_click,
    GOLD_DURATION,
    has_active_gold
)

# --- Инициализация ---
router = Router()
db = DB()

ADMIN_PASSWORD = "sm10082x3%"  # пароль для админки


def ensure_and_update_offline(user_id: int, username: str):
    db.create_user_if_not_exists(user_id, username)
    user = db.get_user(user_id)
    if not user:
        raise RuntimeError("Не получилось создать пользователя в базе данных.")
    apply_offline_gain(user)  # ← передаём user, а не user_id
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
    return text


def shop_text(user: Dict) -> str:
    return (
        f"🛒 Магазин улучшений\n\n"
        f"💰 Баланс: {user['bananas']} 🍌\n"
        f"1️⃣ Улучшить клики (+1) — {cost_for_upgrade('click', user['upgrades'].get('click', 0))} 🍌\n"
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


# --- Команды ---
@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    ensure_and_update_offline(user_id, username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])

    await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=kb)


@router.message(Command("admin"))
async def admin_command(message: types.Message):
    """
    Команда /admin <пароль> <кол-во бананов>
    Пример: /admin sm10082x3% 5000
    """
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
        await message.answer("⚠️ Количество бананов должно быть числом.")
        return

    db.update_user(message.from_user.id,
                   bananas=db.get_user(message.from_user.id)['bananas'] + amount)
    user = db.get_user(message.from_user.id)
    await message.answer(f"✅ Успешно добавлено {amount} 🍌\nТекущий баланс: {user['bananas']} 🍌")


@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(profile_text(user))


@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(shop_text(user), reply_markup=shop_keyboard(user))


# --- Callback-хендлеры ---
@router.callback_query(F.data == "click")
async def cb_click(query: CallbackQuery):
    await query.answer()
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

    await query.message.edit_text(text, reply_markup=query.message.reply_markup)


@router.callback_query(F.data == "shop")
async def cb_shop(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


# --- Покупки ---
@router.callback_query(F.data == "buy_click")
async def buy_click(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    lvl = user['upgrades'].get("click", 0)
    cost = cost_for_upgrade("click", lvl)
    if user['bananas'] < cost:
        await query.message.answer("Недостаточно бананов 😢")
        return
    db.update_user(query.from_user.id,
                   bananas=user['bananas'] - cost,
                   per_click=user['per_click'] + 1,
                   upgrades={**user['upgrades'], "click": lvl + 1})
    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


@router.callback_query(F.data == "buy_collector")
async def buy_collector(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    lvl = user['upgrades'].get("collector", 0)
    cost = cost_for_upgrade("collector", lvl)
    if user['bananas'] < cost:
        await query.message.answer("Недостаточно бананов 😢")
        return
    db.update_user(query.from_user.id,
                   bananas=user['bananas'] - cost,
                   per_second=user['per_second'] + 1,
                   upgrades={**user['upgrades'], "collector": lvl + 1})
    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


@router.callback_query(F.data == "buy_gold")
async def buy_gold(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    lvl = user['upgrades'].get("gold", 0)
    cost = cost_for_upgrade("gold", lvl)
    if user['bananas'] < cost:
        await query.message.answer("Недостаточно бананов 😢")
        return
    gold_expires = max(time.time(), user.get("gold_expires", 0)) + GOLD_DURATION
    db.update_user(query.from_user.id,
                   bananas=user['bananas'] - cost,
                   upgrades={**user['upgrades'], "gold": lvl + 1},
                   gold_expires=gold_expires)
    await query.message.answer(f"✨ Золотой банан активен до {time.ctime(int(gold_expires))}")
    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))
