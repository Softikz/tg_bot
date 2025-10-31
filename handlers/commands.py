# handlers/commands.py
import time
import asyncio
import logging
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
    added, new_last = apply_offline_gain(user)
    if added:
        db.update_user(user_id, bananas=user["bananas"] + added, last_update=new_last)
    return db.get_user(user_id)

def profile_text(user, event=None):
    text = (
        f"👤 Профиль @{user['username']}\n\n"
        f"🍌 Бананы: {int(user['bananas'])}\n"
        f"🖱 За клик: {user['per_click']} (эффективно: {effective_per_click(user, db)})\n"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
    )
    if has_active_gold(user):
        remaining = int(user["gold_expires"] - time.time())
        text += f"✨ Золотой банан активен ({remaining} сек)\n"
    if event:
        text += f"🎉 Активен ивент: {event['type']} (x{event['multiplier']})\n"
    text += f"🔁 Перерождений: {user.get('rebirths', 0)}"
    return text

def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Улучшить клик", callback_data="buy_click")],
        [InlineKeyboardButton(text="⚙️ Улучшить сборщик", callback_data="buy_collector")],
        [InlineKeyboardButton(text="✨ Купить золотой банан", callback_data="buy_gold")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click"),
         InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")]
    ])

# ====== Команды ======
@router.message(Command("start"))
async def start_command(message: types.Message):
    ensure_and_update_offline(message.from_user.id, message.from_user.username or "unknown")
    await message.answer("👋 Добро пожаловать в Banana Bot!", reply_markup=main_menu_keyboard())

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    event = db.get_active_event()
    await message.answer(profile_text(user, event), reply_markup=main_menu_keyboard())

@router.message(Command("event"))
async def event_command(message: types.Message):
    args = message.text.split()
    if len(args) != 4:
        await message.answer("⚠️ Использование: /event <пароль> <тип> <время>")
        return
    _, password, event_type, duration = args
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль.")
        return

    if not event_type.startswith("clickx"):
        await message.answer("⚠️ Поддерживаются только ивенты вида clickxN (например clickx5)")
        return

    try:
        mult = float(event_type.replace("clickx", ""))
        h, m = map(int, duration.split(":"))
        expires = time.time() + h * 3600 + m * 60
    except:
        await message.answer("⚠️ Ошибка в параметрах.")
        return

    db.set_event(event_type, mult, expires)
    await message.answer(f"🎉 Ивент {event_type} запущен на {duration}!")

    asyncio.create_task(stop_event_after(expires))

async def stop_event_after(expires: float):
    await asyncio.sleep(max(0, expires - time.time()))
    db.clear_event()
    log.info("🎉 Ивент завершён!")

async def start_event_recovery(db: DB, bot):
    event = db.get_active_event()
    if event:
        remaining = event["expires"] - time.time()
        if remaining > 0:
            log.info(f"♻️ Восстановлен ивент {event['type']} ({remaining:.0f} сек осталось)")
            asyncio.create_task(stop_event_after(event["expires"]))

# ====== Кнопки ======
@router.callback_query(F.data == "click")
async def click_button(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    per_click = effective_per_click(user, db)
    db.update_user(callback.from_user.id, bananas=user["bananas"] + per_click)
    user = db.get_user(callback.from_user.id)
    await callback.message.edit_text(f"🍌 +{per_click} бананов!\nВсего: {user['bananas']}", reply_markup=main_menu_keyboard())

@router.callback_query(F.data == "shop")
async def shop_button(callback: CallbackQuery):
    await callback.answer()
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    click_cost = cost_for_upgrade("click", user["upgrades"].get("click", 0))
    await callback.message.edit_text(f"🛒 Улучшения\nСтоимость клика: {click_cost} 🍌", reply_markup=shop_keyboard())

@router.callback_query(F.data == "buy_click")
async def buy_click(callback: CallbackQuery):
    user = ensure_and_update_offline(callback.from_user.id, callback.from_user.username)
    level = user["upgrades"].get("click", 0)
    cost = cost_for_upgrade("click", level)
    if user["bananas"] < cost:
        await callback.answer("❌ Недостаточно бананов!", show_alert=True)
        return
    user["bananas"] -= cost
    user["upgrades"]["click"] = level + 1
    db.update_user(callback.from_user.id, bananas=user["bananas"], per_click=calculate_per_click(user["upgrades"]), upgrades=user["upgrades"])
    await callback.answer(f"✅ Куплено! Уровень {level + 1}", show_alert=True)
    await shop_button(callback)

async def stop_event_after(expires: float):
    """Останавливает ивент после окончания"""
    await asyncio.sleep(max(0, expires - time.time()))
    db.clear_event()
    log.info("🎉 Ивент завершён!")

async def start_event_recovery(db: DB, bot):
    """Восстанавливает ивент после перезапуска бота"""
    event = db.get_active_event()
    if event:
        remaining = event["expires"] - time.time()
        if remaining > 0:
            log.info(f"♻️ Восстановлен ивент {event['type']} ({remaining:.0f} сек осталось)")
            asyncio.create_task(stop_event_after(event["expires"]))
