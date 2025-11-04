# handlers/commands.py
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from storage.db import DB
from game.logic import (
    apply_offline_gain, effective_per_click, buy_click_upgrade, buy_passive_upgrade,
    perform_rebirth
)

router = Router()
db = DB()  # локальный экземпляр БД для обработчиков (использует /data/database.db)

# ---- UI ----
def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🖱️ Клик", callback_data="click"),
            InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")
        ],
        [InlineKeyboardButton(text="♻️ Перерождение", callback_data="rebirth")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def shop_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(text="⬆️ Купить апгрейд клика", callback_data="buy_click"),
        InlineKeyboardButton(text="⬆️ Купить пассив (collector)", callback_data="buy_passive"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    )
    return kb

# ---- Команды ----

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    # Создаём пользователя, если нет
    db.create_user_if_not_exists(user.id, user.username or "")
    user_data = db.get_user(user.id)

    # Применяем оффлайн начисление и сохраняем, если есть
    added, new_last = apply_offline_gain(user_data)
    if added:
        db.update_user(user.id, bananas=user_data.get("bananas", 0) + added, last_update=new_last)
        await message.answer(f"Вы получили {added} бананов за время отсутствия!")

    await message.answer(
        f"👋 Привет, {user.first_name}!\n"
        f"Ваш баланс: {user_data.get('bananas', 0)} бананов\n"
        f"Уровень клика: {user_data.get('upgrades', {}).get('click', 0)}\n"
        f"Пассив: {user_data.get('upgrades', {}).get('collector', 0)}\n"
        f"Перерождений: {user_data.get('rebirths', 0)}",
        reply_markup=main_keyboard(user.id)
    )

# ---- Callback handlers ----

@router.callback_query(lambda c: c.data == "click")
async def handle_click(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.message.answer("❌ Сначала отправьте /start чтобы создать аккаунт.")
        return

    # Apply offline gain first
    added, new_last = apply_offline_gain(user)
    if added:
        db.update_user(user_id, bananas=user.get("bananas", 0) + added, last_update=new_last)
        user = db.get_user(user_id)  # refresh

    per_click = effective_per_click(user)
    new_bananas = user.get("bananas", 0) + per_click
    db.update_user(user_id, bananas=new_bananas, last_update=new_last)

    await callback.message.answer(f"🖱️ Вы кликнули и получили {per_click} бананов! Баланс: {new_bananas}")
    # Обновим клавиатуру (необязательно)
    try:
        await callback.message.edit_reply_markup(reply_markup=main_keyboard(user_id))
    except Exception:
        pass

@router.callback_query(lambda c: c.data == "shop")
async def open_shop(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.message.answer("❌ Сначала /start")
        return

    await callback.message.answer(
        f"🛒 Магазин\n\nБаланс: {user.get('bananas', 0)} бананов\n"
        f"Уровень клика: {user.get('upgrades', {}).get('click', 0)}\n"
        f"Уровень пассива: {user.get('upgrades', {}).get('collector', 0)}",
        reply_markup=shop_keyboard(user_id)
    )

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=main_keyboard(callback.from_user.id))

@router.callback_query(lambda c: c.data == "buy_click")
async def handle_buy_click(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.message.answer("❌ Сначала /start")
        return

    success, msg = buy_click_upgrade(db, user_id, user)
    await callback.message.answer(msg)
    # Optionally refresh shop/main
    user = db.get_user(user_id)
    await callback.message.answer(f"Баланс: {user.get('bananas', 0)}", reply_markup=shop_keyboard(user_id))

@router.callback_query(lambda c: c.data == "buy_passive")
async def handle_buy_passive(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.message.answer("❌ Сначала /start")
        return

    success, msg = buy_passive_upgrade(db, user_id, user)
    await callback.message.answer(msg)
    user = db.get_user(user_id)
    await callback.message.answer(f"Баланс: {user.get('bananas', 0)}", reply_markup=shop_keyboard(user_id))

@router.callback_query(lambda c: c.data == "rebirth")
async def handle_rebirth(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if not user:
        await callback.message.answer("❌ Сначала /start")
        return

    success, msg = perform_rebirth(db, user_id, user)
    await callback.message.answer(msg)
    # Если есть анимация — она должна запускаться на стороне клиента/кнопки; тут — ответ
    user = db.get_user(user_id)
    await callback.message.answer(
        f"Баланс: {user.get('bananas',0)}\n"
        f"Уровень клика: {user.get('upgrades', {}).get('click',0)}\n"
        f"Перерождений: {user.get('rebirths',0)}",
        reply_markup=main_keyboard(user_id)
    )

