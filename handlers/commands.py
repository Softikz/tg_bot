# handlers/commands.py
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time
import asyncio
from typing import Dict
import logging


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
log = logging.getLogger(__name__)
# --- Вспомогательные функции ---
def ensure_and_update_offline(user_id: int, username: str):
    """
    Убедиться, что пользователь есть в БД, применить оффлайн доход (если есть) и вернуть свежие данные.
    """
    db.create_user_if_not_exists(user_id, username)
    user = db.get_user(user_id)
    if not user:
        raise RuntimeError("Не получилось создать пользователя в базе данных.")
    # apply_offline_gain возвращает (added, new_last)
    added, new_last = apply_offline_gain(user)
    if added:
        # если накопилось бананов за оффлайн — сохранить в БД
        new_bananas = user.get("bananas", 0) + added
        db.update_user(user_id, bananas=new_bananas, last_update=new_last)
    # вернуть актуальные данные
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
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])


# --- Команды ---
@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    ensure_and_update_offline(user_id, username)

    kb = main_menu_keyboard()
    await message.answer("👋 Добро пожаловать в Banana Bot!\nНакликай себе бананы!", reply_markup=kb)


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
        await message.answer("⚠️ Количество бананов должно быть числом.")
        return

    db.update_user(message.from_user.id,
                   bananas=db.get_user(message.from_user.id)['bananas'] + amount)
    user = db.get_user(message.from_user.id)
    await message.answer(f"✅ Успешно добавлено {amount} 🍌\nТекущий баланс: {user['bananas']} 🍌")


@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = ensure_and_update_offline(message.from_user.id, message.from_user.username)
    await message.answer(profile_text(user), reply_markup=main_menu_keyboard())


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
    # оставляем ту же клавиатуру, что была (если сообщение имело клавиатуру)
    reply_kb = query.message.reply_markup or main_menu_keyboard()
    await query.message.edit_text(text, reply_markup=reply_kb)


@router.callback_query(F.data == "shop")
async def cb_shop(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


# --- Покупка апгрейдов ---
@router.callback_query(F.data.in_({"buy_click", "buy_collector", "buy_gold"}))
async def cb_buy_upgrade(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    upgrades = user.get("upgrades", {})
    data = query.data.replace("buy_", "")  # "click", "collector" или "gold"

    # текущий уровень и стоимость
    level = upgrades.get(data, 0)
    try:
        cost = cost_for_upgrade(data, level)
    except Exception:
        await query.answer("Ошибка расчёта стоимости.", show_alert=True)
        return

    if user["bananas"] < cost:
        await query.answer("❌ Недостаточно бананов!", show_alert=True)
        return

    new_bananas = user["bananas"] - cost
    new_upgrades = upgrades.copy()
    new_upgrades[data] = level + 1

    if data == "click":
        db.update_user(query.from_user.id, bananas=new_bananas, per_click=user["per_click"] + 1, upgrades=new_upgrades)
    elif data == "collector":
        db.update_user(query.from_user.id, bananas=new_bananas, per_second=user["per_second"] + 1, upgrades=new_upgrades)
    elif data == "gold":
        # устанавливваем время окончания эффекта на сейчас + длительность
        expires = time.time() + GOLD_DURATION
        db.update_user(query.from_user.id, bananas=new_bananas, gold_expires=expires, upgrades=new_upgrades)

    user = db.get_user(query.from_user.id)
    await query.message.edit_text(shop_text(user), reply_markup=shop_keyboard(user))


# --- Возврат в главное меню ---
@router.callback_query(F.data == "profile")
async def cb_profile(query: CallbackQuery):
    await query.answer()
    user = ensure_and_update_offline(query.from_user.id, query.from_user.username)
    await query.message.edit_text(profile_text(user), reply_markup=main_menu_keyboard())


# --- Перерождение ---
REQUIREMENTS = [
    {"bananas": 500, "gold": 0},   # первое перерождение
    {"bananas": 1000, "gold": 1},  # второе и далее
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
        f"{bar} {progress_percent}%",
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

    new_upgrades = user["upgrades"].copy()
    if req.get("gold", 0) > 0:
        new_upgrades["gold"] = max(0, new_upgrades.get("gold", 0) - req["gold"])

    db.update_user(query.from_user.id, bananas=0, per_click=1, per_second=0, upgrades=new_upgrades)
    db.update_user(query.from_user.id, rebirths=rebirth_count + 1)

    await query.message.answer("🌟 Вы переродились! Прогресс сброшен, получен бонус пассивного дохода.")


# --- 📢 Рассылка всем пользователям ---
@router.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    """
    Рассылка всем пользователям.
    Пример: /broadcast sm10082x3% Технические работы через 5 минут.
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Использование: /broadcast <пароль> <текст>")
        return

    _, password, text = args
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль.")
        return

    users = db.get_all_users()
    total = len(users)
    sent = 0

    for u in users:
        try:
            await message.bot.send_message(u["user_id"], f"📢 {text}")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            continue


    @router.callback_query()
    async def _debug_unhandled_callback(query: CallbackQuery):
        # если уже был обработан — ничего не сделаем (aiogram не вызывает этот хендлер, если ранее совпал другой)
        # но если сюда попадаем — значит для этого callback_data не найден конкретный хендлер
        log.info("⚠️ Unhandled callback_query received. from=%s data=%s message_id=%s",
                 query.from_user.id, query.data, getattr(query.message, "message_id", None))
        # ответим пользователю маленьким alert, чтобы было видно в клиенте
        try:
            await query.answer(f"Неизвестная кнопка: {query.data}", show_alert=False)
        except Exception:
            pass
        # отправим подробный лог в чат (удалите/закомментируйте в продакшене)
        try:
            await query.message.reply(f"DEBUG: callback_data = <code>{query.data}</code>")
        except Exception:
            pass

    # Логируем все обычные сообщения, которые не попали под другие handlers
    @router.message()
    async def _debug_unhandled_message(message: types.Message):
        log.info("⚠️ Unhandled message: from=%s text=%s", message.from_user.id, message.text)
        # не отвечаем пользователю, только лог
        # если хотите — можно присылать подсказку:
        # await message.reply("Я не распознал это сообщение. Воспользуйтесь кнопками в меню.")

    percent = (sent / total * 100) if total else 0
    await message.answer(f"✅ Отправлено {sent}/{total} пользователям ({percent:.1f}%)")
