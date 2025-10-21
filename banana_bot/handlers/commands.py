# handlers/commands.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time
import asyncio
from typing import Dict

from banana_bot.storage.db import DB
from banana_bot.game.logic import (
    apply_offline_gain,
    cost_for_upgrade,
    effective_per_click,
    GOLD_DURATION,
    has_active_gold
)

# --- Инициализация ---
router = Router()
db = DB()


# --- Вспомогательные функции ---
def ensure_and_update_offline(user_id: int, username: str):
    """Создает пользователя, если его нет, и применяет оффлайн-награду."""
    db.create_user_if_not_exists(user_id, username)
    user = db.get_user(user_id)
    if not user:
        raise RuntimeError("Не получилось создать пользователя в базе данных.")
    apply_offline_gain(user_id)
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


def reset_user_progress(self, user_id: int):
    """Сбрасывает бананы, клики и пассив до начальных значений"""
    self.update_user(user_id, bananas=0, per_click=1, per_second=0, upgrades={})

def add_gold_banana(self, user_id: int, count: int = 1):
    """Начисление золотых бананов (условно)"""
    user = self.get_user(user_id)
    upgrades = user['upgrades']
    upgrades['gold_banana'] = upgrades.get('gold_banana', 0) + count
    self.update_user(user_id, upgrades=upgrades)

def add_passive_clicks(self, user_id: int, count: int = 1):
    """Добавляет пассивные клики"""
    user = self.get_user(user_id)
    self.update_user(user_id, per_second=user['per_second'] + count)



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

    text = f"🍌 Клик! +{per_click}\n\nВсего: {user['bananas']} 🍌\nЗа клик: {user['per_click']}\nПассив: {user['per_second']}/сек\n"
    if has_active_gold(user):
        text += "✨ Активен Золотой Банан (2×)\n"

    try:
        await query.message.edit_text(text, reply_markup=query.message.reply_markup)
    except Exception:
        await query.message.answer(text)


@router.callback_query(F.data == "profile")
async def cb_profile(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])
    try:
        await query.message.edit_text(profile_text(user), reply_markup=kb)
    except Exception:
        await query.message.answer(profile_text(user), reply_markup=kb)


@router.callback_query(F.data == "shop")
async def cb_shop(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    try:
        await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))
    except Exception:
        await query.message.answer(shop_text(user), reply_markup=shop_keyboard(user))


# --- Магазин покупок ---
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
    try:
        await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))
    except Exception:
        pass


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
    try:
        await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))
    except Exception:
        pass


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
    try:
        await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))
    except Exception:
        pass


# --- Читы для теста ---
@router.callback_query(F.data == "cheat_bananas")
async def cheat_bananas(query: CallbackQuery):
    await query.answer("✅ Добавлено 1000 бананов (только для теста)")
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    db.update_user(query.from_user.id, bananas=user['bananas'] + 1000)
    user = db.get_user(query.from_user.id)
    try:
        await query.message.edit_text(profile_text(user), reply_markup=query.message.reply_markup)
    except Exception:
        await query.message.answer(profile_text(user))


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

    # Сбрасываем прогресс
    db.reset_user_progress(user_id)
    db.add_gold_banana(user_id, 1)
    db.add_passive_clicks(user_id, 2)

    # Мини-анимация
    for msg in ["✨ Перерождение... 🍌", "🌟 Перерождение почти завершено...", "💫 Почти готово!"]:
        await query.message.edit_text(msg)
        await asyncio.sleep(1.2)

    # Финальное сообщение
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
