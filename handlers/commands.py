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

router = Router()
db = DB()


# --- Расширяем класс DB прямо здесь ---
def reset_user_progress(user_id: int):
    """Сбрасывает бананы, клики и пассив до начальных значений"""
    db.update_user(user_id, bananas=0, per_click=1, per_second=0, upgrades={})


def add_gold_banana(user_id: int, count: int = 1):
    """Добавляет золотой банан"""
    user = db.get_user(user_id)
    upgrades = user.get('upgrades', {})
    upgrades['gold_banana'] = upgrades.get('gold_banana', 0) + count
    db.update_user(user_id, upgrades=upgrades)


def add_passive_clicks(user_id: int, count: int = 1):
    """Добавляет пассивные клики"""
    user = db.get_user(user_id)
    db.update_user(user_id, per_second=user['per_second'] + count)


# --- Основные функции ---
def ensure_and_update_offline(user_id: int, username: str):
    db.create_user_if_not_exists(user_id, username)
    user = db.get_user(user_id)
    apply_offline_gain(user)
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
        f"1️⃣ Увеличить клики (+1) — {cost_for_upgrade('click', user['upgrades'].get('click', 0))} 🍌\n"
        f"2️⃣ Увеличить пассив (+1/сек) — {cost_for_upgrade('collector', user['upgrades'].get('collector', 0))} 🍌\n"
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
        [InlineKeyboardButton(text="💰 Накрутить бананы", callback_data="cheat_bananas")]
    ])

    await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=kb)


@router.callback_query(F.data == "click")
async def cb_click(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    per_click = effective_per_click(user)
    db.update_user(query.from_user.id, bananas=user['bananas'] + per_click, last_update=time.time())
    user = db.get_user(query.from_user.id)

    text = f"🍌 Клик! +{per_click}\n\nВсего: {user['bananas']} 🍌"
    if has_active_gold(user):
        text += "\n✨ Активен Золотой Банан (2×)"

    await query.message.edit_text(text, reply_markup=query.message.reply_markup)


# --- Перерождение ---
@router.callback_query(F.data == "rebirth")
async def rebirth_prompt(query: CallbackQuery):
    await query.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="confirm_rebirth")
    builder.button(text="Отмена", callback_data="shop")
    await query.message.edit_text(
        "🔁 Готовы переродиться? 🎉\nВзамен вы получите:\n"
        "- бесплатный золотой банан ✨\n"
        "- +2 к пассиву\n",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "confirm_rebirth")
async def confirm_rebirth(query: CallbackQuery):
    await query.answer()
    user_id = query.from_user.id

    reset_user_progress(user_id)
    add_gold_banana(user_id, 1)
    add_passive_clicks(user_id, 2)

    for msg in ["✨ Перерождение... 🍌", "🌟 Почти готово...", "💫 Готово!"]:
        await query.message.edit_text(msg)
        await asyncio.sleep(1.2)

    user = db.get_user(user_id)
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Магазин", callback_data="shop")
    builder.button(text="🔁 Перерождение", callback_data="rebirth")

    await query.message.edit_text(
        "🌟 Вы переродились!\n\n"
        "🥇 Получен 1 золотой банан!\n"
        "➕ Пассивный доход увеличен на +2 🍌\n"
        "Теперь начните путь заново!",
        reply_markup=builder.as_markup()
    )
