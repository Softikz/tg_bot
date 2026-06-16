from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, CROP_SELL_PRICE, ADMIN_ID, users
from keyboards import farm_kb, city_kb, main_menu_kb, profile_kb
from datetime import datetime
from typing import Optional
from aiogram import Bot

# bot будет установлен из main.py
bot: Optional[Bot] = None

router = Router()

@router.message(Command("start"))
async def start_command(message: types.Message):
    user = get_user(message.from_user.id)
    if not user.get("name"):
        user["name"] = message.from_user.full_name or "Фермер"

    if not user.get("tutorial_complete"):
        await message.answer(
            "🌾 Добро пожаловать на ферму!\n\n"
            "Привет! Я Пиги! 🐷\n"
            "Добро пожаловать на ферму!\n"
            "Я помогу тебе освоиться и стать настоящим фермером!\n"
            "Готов начать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать обучение!", callback_data="tutorial_start")]
            ])
        )
    else:
        await message.answer(
            "👋 Добро пожаловать на Ферму!\n\n"
            "Используйте кнопки внизу для навигации:\n\n"
            "• 🌱 Кликайте на грядку, чтобы сажать семена\n"
            "• 🍒 Продавайте урожай на овощебазе в городе\n"
            "• 🌿 Расширяйте грядки и изучайте новые культуры\n"
            "• 🙌 Посещайте соседей и заводите новых друзей",
            reply_markup=main_menu_kb()
        )

@router.message(Command("farm"))
async def farm_command(message: types.Message):
    await message.answer(
        "🌱 Ваша ферма, нажмите на грядку чтобы посадить или собрать урожай",
        reply_markup=farm_kb(message.from_user.id)
    )

@router.message(Command("city"))
async def city_command(message: types.Message):
    await message.answer(
        "🌃 Город\n\nЗдесь вы можете взаимодействовать с городскими учреждениями, выполнять задания",
        reply_markup=city_kb()
    )

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = get_user(message.from_user.id)
    vip_text = ""
    if user.get("vip_until"):
        vip_dt = user["vip_until"]
        if isinstance(vip_dt, str):
            vip_dt = datetime.fromisoformat(vip_dt)
        if vip_dt > datetime.now():
            vip_text = f"\n👑 VIP статус: Активен (до {vip_dt.strftime('%d.%m.%y, %H:%M')})"

    text = (
        f"👤 Профиль игрока\n\n"
        f"📝 Имя: {user.get('name', 'Фермер')}{vip_text}\n"
        f"⭐ Титул: {user.get('title', 'Новичок')}\n"
        f"🏆 Уровень: {user.get('level', 1)}\n"
        f"🔹 Опыт: {user.get('exp', 0)}/{100 * user.get('level', 1)}\n"
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

    # Ресурсы
    resources = user.get("harvest", {})
    res_text = ""
    for res in ["🪵 древесина", "🪨 камень", "🔗 железо", "📄 чертеж", "🌿 Силос", "🥜 Комбикорм", "💩 Удобрение"]:
        if resources.get(res, 0) > 0:
            res_text += f"{res}: {resources[res]}\n"
    if res_text:
        text += f"\n📦 Ресурсы:\n{res_text}"

    await message.answer(text, reply_markup=profile_kb(message.from_user.id))

@router.message(Command("friends"))
async def friends_command(message: types.Message):
    await message.answer(
        "👥 Друзья и соседи\n\nПосещайте фермы других игроков, помогайте им и заводите новых друзей!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Рейтинги", callback_data="ratings")],
            [InlineKeyboardButton(text="🔎 Найти соседей", callback_data="find_neighbors")],
            [InlineKeyboardButton(text="🎣 Озеро", callback_data="fishing_enter")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")],
        ])
    )

@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = get_user(message.from_user.id)
    text = (
        "🏪 Магазин\n\n"
        f"💰 Монеты: {user.get('money', 0)}\n"
        f"⭐ Звёзды: {user.get('stars', 0)}\n\n"
        "Выберите раздел:"
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Семена", callback_data="shop_seeds")],
        [InlineKeyboardButton(text="🟫 Грядки", callback_data="shop_beds")],
        [InlineKeyboardButton(text="🔧 Инструменты", callback_data="shop_tools")],
        [InlineKeyboardButton(text="⭐ Премиум магазин", callback_data="shop_premium")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")],
    ]))

@router.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_menu_kb())

@router.message(Command("help"))
async def help_command(message: types.Message):
    text = (
        "📋 Список команд:\n\n"
        "/farm — 🌾 На ферму\n"
        "/city — 🚗 В город\n"
        "/profile — 👤 Профиль\n"
        "/friends — 👥 Друзья и соседи\n"
        "/shop — 🏪 Магазин\n"
        "/menu — 🏠 Главное меню\n"
        "/help — ❓ Помощь"
    )
    await message.answer(text)


# ====== ADMIN COMMANDS ======

class BroadcastState:
    """Простое хранилище состояния для команды /broadcast"""
    waiting_for_message = {}


@router.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    """Команда /broadcast доступна только админу"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer(
        "📢 Режим рассылки активирован\n\n"
        "Отправьте сообщение, которое нужно разослать всем пользователям.\n"
        "Используйте /cancel для отмены.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
        ])
    )
    BroadcastState.waiting_for_message[message.from_user.id] = True


@router.message(F.text, F.from_user.id == ADMIN_ID)
async def broadcast_send(message: types.Message):
    """Отправляет сообщение всем пользователям"""
    # Проверяем находимся ли в режиме рассылки
    if message.from_user.id not in BroadcastState.waiting_for_message:
        return
    
    # Удаляем из ожидающих
    BroadcastState.waiting_for_message.pop(message.from_user.id, None)
    
    # Отправляем всем пользователям
    sent_count = 0
    error_count = 0
    
    await message.answer("📤 Начинаю рассылку...", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    
    for user_id in list(users.keys()):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Объявление от администратора:</b>\n\n{message.text}"
            )
            sent_count += 1
        except Exception as e:
            error_count += 1
            # Тихо пропускаем ошибки для недоступных пользователей
    
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {sent_count}\n"
        f"❌ Ошибок: {error_count}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
        ])
    )


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(call: types.CallbackQuery):
    """Отмена режима рассылки"""
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ У вас нет доступа")
        return
    
    BroadcastState.waiting_for_message.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Режим рассылки отменён")
    await call.answer()


@router.message(Command("cancel"))
async def cancel_broadcast(message: types.Message):
    """Отмена любого процесса через /cancel"""
    if message.from_user.id == ADMIN_ID and message.from_user.id in BroadcastState.waiting_for_message:
        BroadcastState.waiting_for_message.pop(message.from_user.id, None)
        await message.answer("❌ Режим рассылки отменён")


