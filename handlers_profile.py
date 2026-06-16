from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import get_user, CROP_SELL_PRICE, VIP_PRICE, VIP_DURATION
from keyboards import profile_kb
from datetime import datetime, timedelta

router = Router()

class NameChange(StatesGroup):
    waiting_name = State()

@router.callback_query(F.data == "profile")
async def profile_callback(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    await show_profile(call.message, user, call.from_user.id, edit=True)

async def show_profile(message, user, user_id, edit=False):
    vip_text = ""
    if user.get("vip_until"):
        vip_dt = user["vip_until"]
        if isinstance(vip_dt, str):
            vip_dt = datetime.fromisoformat(vip_dt)
        if vip_dt > datetime.now():
            remaining = vip_dt - datetime.now()
            days = remaining.days
            hours = remaining.seconds // 3600
            vip_text = f"\n👑 VIP статус: Активен (ещё {days}д {hours}ч)"

    exp_current = user.get("exp", 0)
    level = user.get("level", 1)
    exp_needed = 100 * level

    text = (
        f"👤 Профиль игрока\n\n"
        f"📝 Имя: {user.get('name', 'Фермер')}{vip_text}\n"
        f"⭐ Титул: {user.get('title', 'Новичок')}\n"
        f"🏆 Уровень: {level}\n"
        f"🔹 Опыт: {exp_current}/{exp_needed}\n"
        f"💰 Монеты: {user.get('money', 0)}\n"
        f"⭐ Звёзды: {user.get('stars', 10)}\n"
        f"🟫 Грядки: {user.get('beds', 2)}\n"
        f"📃 Разрешения: {user.get('permissions', 0)}\n"
        f"🎟️ Билеты удачи: {user.get('luck_tickets', 0)}\n\n"
        f"🌱 Семена:\n"
    )

    seeds = user.get("seeds", {})
    has_seeds = False
    for seed, count in seeds.items():
        if count > 0:
            text += f"{seed} Семена: {count}\n"
            has_seeds = True
    if not has_seeds:
        text += "Нет семян\n"

    text += "\n🏚️ Урожай:\n"
    harvest = user.get("harvest", {})
    has_harvest = False
    for item, count in harvest.items():
        if count > 0 and item in CROP_SELL_PRICE:
            text += f"{item}: {count} шт.\n"
            has_harvest = True
    if not has_harvest:
        text += "Нет урожая\n"

    resources = user.get("harvest", {})
    res_text = ""
    for res in ["🪵 древесина", "🪨 камень", "🔗 железо", "📄 чертеж", "🌿 Силос", "🥜 Комбикорм", "💩 Удобрение"]:
        if resources.get(res, 0) > 0:
            res_text += f"{res}: {resources[res]}\n"
    if res_text:
        text += f"\n📦 Ресурсы:\n{res_text}"

    if edit:
        await message.edit_text(text, reply_markup=profile_kb(user_id))
    else:
        await message.answer(text, reply_markup=profile_kb(user_id))

@router.callback_query(F.data.startswith("claim_level_reward_"))
async def claim_level_reward(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    level = int(call.data.replace("claim_level_reward_", ""))
    reward_key = f"level_reward_{level}"

    if user.get(reward_key):
        await call.answer("❌ Награда уже получена!")
        return

    rewards = {
        1: {"seeds": {"🧅": 5}},
        2: {"seeds": {"🥔": 5}, "stars": 3},
        3: {"seeds": {"🌾": 5}, "stars": 5},
        4: {"seeds": {"🍓": 5}, "stars": 7},
        5: {"tickets": 3, "stars": 10},
        6: {"seeds": {"🌽": 5}, "stars": 12},
        7: {"seeds": {"🍇": 5}, "stars": 15},
        8: {"seeds": {"🍚": 5}, "stars": 18},
        9: {"seeds": {"🎃": 5}, "stars": 20},
        10: {"blueprint": 1, "stars": 25, "tickets": 5},
    }

    reward = rewards.get(level, {"stars": 5})
    if "seeds" in reward:
        for seed, amount in reward["seeds"].items():
            user["seeds"][seed] = user["seeds"].get(seed, 0) + amount
    if "stars" in reward:
        user["stars"] = user.get("stars", 0) + reward["stars"]
    if "tickets" in reward:
        user["luck_tickets"] = user.get("luck_tickets", 0) + reward["tickets"]
    if "blueprint" in reward:
        user["harvest"]["📄 чертеж"] = user["harvest"].get("📄 чертеж", 0) + reward["blueprint"]

    user[reward_key] = True
    await call.answer(f"🎁 Получена награда за {level} уровень!")
    await profile_callback(call)

@router.callback_query(F.data == "change_name")
async def change_name_start(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    if user.get("money", 0) < 50000:
        await call.answer(f"❌ Недостаточно монет! Нужно 💰50000, у вас 💰{user.get('money', 0)}")
        return

    await call.message.edit_text(
        "✏️ Напиши новое имя для смены:\n\n(не более 10 символов)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="profile")]
        ])
    )
    await state.set_state(NameChange.waiting_name)

@router.message(NameChange.waiting_name)
async def change_name_done(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    new_name = message.text.strip()

    if len(new_name) > 10:
        await message.answer("❌ Имя не должно превышать 10 символов! Попробуйте ещё раз:")
        return

    if user.get("money", 0) < 50000:
        await message.answer("❌ Недостаточно монет!")
        await state.clear()
        return

    user["money"] -= 50000
    user["name"] = new_name
    await message.answer(f"✅ Имя изменено на «{new_name}»!")
    await state.clear()
    await show_profile(message, user, message.from_user.id)

# ==================== VIP ====================
@router.callback_query(F.data == "become_vip")
async def vip_info(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("vip_until"):
        vip_dt = user["vip_until"]
        if isinstance(vip_dt, str):
            vip_dt = datetime.fromisoformat(vip_dt)
        if vip_dt > datetime.now():
            await call.answer("👑 VIP уже активен!")
            return

    await call.message.edit_text(
        "👑 VIP подписка\n\n"
        "✨ Станьте VIP игроком и получите:\n"
        "👑 Кастомный эмодзи к своему имени\n"
        "🌱 Дополнительную VIP грядку, защищенную от воровства\n"
        "⚡ Удобные кнопки для массового управления фермой\n"
        "👑 Особый статус в профиле (VIP)\n\n"
        f"💰 Стоимость: {VIP_PRICE}⭐\n"
        "⏰ Длительность: одна неделя\n\n"
        f"⭐ У вас сейчас: {user.get('stars', 0)}⭐",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Купить подписку", callback_data="buy_vip")],
            [InlineKeyboardButton(text="🎁 Бесплатный VIP", callback_data="free_vip_request")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]
        ])
    )

@router.callback_query(F.data == "buy_vip")
async def buy_vip(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("stars", 0) < VIP_PRICE:
        await call.answer(f"❌ Недостаточно ⭐! Нужно {VIP_PRICE}⭐, у вас {user.get('stars', 0)}⭐")
        return

    user["stars"] -= VIP_PRICE
    user["vip_until"] = datetime.now() + VIP_DURATION
    user["beds"] += 1
    user["beds_data"].append({"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None})

    await call.message.edit_text(
        "🎉 Поздравляем с активацией VIP подписки! 👑\n\n"
        "✨ Теперь вы можете:\n"
        "🌱 Использовать дополнительную VIP грядку, защищенную от воровства\n"
        "🍂 Не беспокоиться об увядании цветов на клумбе\n"
        "⚡️ Использовать удобные кнопки массового управления фермой\n"
        "⚙️ Управлять автопродлением подписки\n\n"
        "👤 Зайдите в Профиль для управления VIP.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
        ])
    )

# ==================== УПРАВЛЕНИЕ VIP ====================
@router.callback_query(F.data == "manage_vip")
async def manage_vip(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    vip_dt = user.get("vip_until")
    if isinstance(vip_dt, str):
        vip_dt = datetime.fromisoformat(vip_dt)

    if not vip_dt or vip_dt <= datetime.now():
        await call.answer("👑 VIP не активен")
        await profile_callback(call)
        return

    remaining = vip_dt - datetime.now()
    days = remaining.days
    hours = remaining.seconds // 3600

    auto_renew = "✅ Включено" if user.get("vip_auto_renew") else "❌ Отключено"

    text = (
        "👑 Управление VIP подпиской\n\n"
        f"📅 Статус: Активен\n"
        f"⏰ Осталось: {days}д {hours}ч\n"
        f"🔄 Автопродление: {auto_renew}\n\n"
        "⚙️ Выберите действие:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Автопродление: Включить" if not user.get("vip_auto_renew") else "🔄 Автопродление: Отключить",
            callback_data="toggle_vip_auto"
        )],
        [InlineKeyboardButton(text=f"⏰ Продлить VIP (99⭐)", callback_data="renew_vip")],
        [InlineKeyboardButton(text="⬅️ В профиль", callback_data="profile")],
    ])
    await call.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "toggle_vip_auto")
async def toggle_vip_auto(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("vip_auto_renew"):
        user["vip_auto_renew"] = False
        await call.answer("🔄 Автопродление отключено")
    else:
        user["vip_auto_renew"] = True
        await call.answer("🔄 Автопродление включено")

    await manage_vip(call)

@router.callback_query(F.data == "renew_vip")
async def renew_vip(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("stars", 0) < VIP_PRICE:
        await call.answer(f"❌ Недостаточно ⭐! Нужно {VIP_PRICE}⭐, у вас {user.get('stars', 0)}⭐")
        return

    user["stars"] -= VIP_PRICE

    vip_dt = user.get("vip_until")
    if isinstance(vip_dt, str):
        vip_dt = datetime.fromisoformat(vip_dt)

    if vip_dt and vip_dt > datetime.now():
        user["vip_until"] = vip_dt + VIP_DURATION
    else:
        user["vip_until"] = datetime.now() + VIP_DURATION

    await call.answer("✅ VIP продлён на неделю!")
    await manage_vip(call)

# ==================== БЕСПЛАТНЫЙ VIP (заявка админу) ====================
@router.callback_query(F.data == "free_vip_request")
async def free_vip_request(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("vip_request_pending"):
        await call.answer("⏳ Заявка уже подана! Ожидайте решения.")
        return

    await call.message.edit_text(
        "🎁 Бесплатный VIP\n\n"
        "❓ Вы вправду хотите получить VIP подписку?\n\n"
        "📝 Если да, подайте заявление на получение VIP подписки по кнопке ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Подать заявление", callback_data="submit_vip_request")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="become_vip")],
        ])
    )

@router.callback_query(F.data == "submit_vip_request")
async def submit_vip_request(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    user["vip_request_pending"] = True

    await call.message.edit_text(
        "📝 Заявка подана!\n\n"
        "⏳ Ожидайте решения администратора.\n"
        "📬 Вам придёт уведомление.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
        ])
    )

    # Отправляем админу
    ADMIN_ID = 5748972158
    try:
        from config import bot
        await bot.send_message(
            ADMIN_ID,
            f"📬 Новая заявка на VIP!\n\n"
            f"👤 Пользователь: {user['name']}\n"
            f"🆔 ID: {call.from_user.id}\n"
            f"⭐ Уровень: {user.get('level', 1)}\n"
            f"💰 Монет: {user.get('money', 0)}\n\n"
            f"❓ Одобрить или отказать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_vip_{call.from_user.id}"),
                    InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_vip_{call.from_user.id}")
                ],
            ])
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

@router.callback_query(F.data.startswith("approve_vip_"))
async def approve_vip(call: types.CallbackQuery):
    ADMIN_ID = 5748972158
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только для администратора!")
        return

    user_id = int(call.data.replace("approve_vip_", ""))
    user = get_user(user_id)

    user["vip_request_pending"] = False
    user["vip_until"] = datetime.now() + VIP_DURATION
    user["beds"] = user.get("beds", 2) + 1
    user["beds_data"].append({"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None})

    await call.message.edit_text(
        f"✅ Заявка одобрена!\n\n"
        f"👤 {user['name']} получил VIP на неделю.",
        reply_markup=None
    )

    try:
        from config import bot
        await bot.send_message(
            user_id,
            "🎉 Поздравляем!\n\n"
            "✅ Ваша заявка на VIP одобрена!\n\n"
            "👑 VIP подписка активирована на 7 дней!\n"
            "🌱 Дополнительная грядка добавлена!\n"
            "⚡ Доступны кнопки массового управления!\n\n"
            "👤 Проверьте профиль — /profile",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
            ])
        )
    except:
        pass

@router.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip(call: types.CallbackQuery):
    ADMIN_ID  = 5748972158
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только для администратора!")
        return

    user_id = int(call.data.replace("reject_vip_", ""))
    user = get_user(user_id)
    user["vip_request_pending"] = False

    await call.message.edit_text(
        f"❌ Заявка отклонена.\n\n👤 {user['name']}",
        reply_markup=None
    )

    try:
        from config import bot
        await bot.send_message(
            user_id,
            "😔 К сожалению, ваша заявка на VIP была отклонена.\n\n"
            "Вы можете подать заявку снова позже или купить VIP за ⭐99.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Премиум магазин", callback_data="shop_premium")]
            ])
        )
    except:
        pass

@router.callback_query(F.data == "noop")
async def noop(call: types.CallbackQuery):
    await call.answer("—")