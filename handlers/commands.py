# handlers/commands.py
import time
import logging
import asyncio
import hashlib
from typing import Dict

from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from storage.db import DB
from game.logic import (
    apply_offline_gain,
    cost_for_upgrade,
    effective_per_click,
    has_active_event,
    calculate_per_click,
    calculate_per_second,
    parse_event_duration,
    get_rebirth_requirement,
    get_rebirth_reward,
    buy_click_upgrade,
    buy_passive_upgrade,
    buy_banana,
    use_banana,
    perform_rebirth,
    get_banana_data,
    get_active_bananas_info,
    get_total_multiplier,
    has_active_bananas,
    BANANA_TYPES
)

router = Router()
db = DB()
ADMIN_PASSWORD = "sm10082x3%"
ADMIN_ID = 5748972158
log = logging.getLogger(__name__)

# Состояния для админ-панели
class AdminStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_bananas_amount = State()
    waiting_for_event_type = State()
    waiting_for_event_duration = State()

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_password = State()
    waiting_for_login = State()

# Список доступных ивентов
AVAILABLE_EVENTS = {
    "event_update_2x": {"name": "🎉 Ивент в честь обновления x2", "multiplier": 2.0},
    "event_update_3x": {"name": "🎊 Ивент в честь обновления x3", "multiplier": 3.0},
    "event_update_5x": {"name": "🚀 Ивент в честь обновления x5", "multiplier": 5.0},
    "event_weekend_2x": {"name": "🎯 Выходной ивент x2", "multiplier": 2.0},
    "event_special_4x": {"name": "💎 Специальный ивент x4", "multiplier": 4.0}
}

# Хеширование пароля
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Проверка существования никнейма
def is_nickname_taken(nickname: str) -> bool:
    users = db.all_users()
    for user in users:
        if user.get("nickname", "").lower() == nickname.lower():
            return True
    return False

# Получение пользователя по никнейму
def get_user_by_nickname(nickname: str):
    users = db.all_users()
    for user in users:
        if user.get("nickname", "").lower() == nickname.lower():
            return user
    return None

# Обновленная функция для работы с пользователями
def ensure_and_update_offline(user_id: int):
    user = db.get_user(user_id)
    if not user:
        return None
    added, new_last = apply_offline_gain(user)
    if added:
        new_bananas = user.get("bananas", 0) + added
        db.update_user(user_id, bananas=new_bananas, last_update=new_last)
    return db.get_user(user_id)

def create_progress_bar(current: int, total: int, size: int = 10) -> str:
    percentage = min(100, int(current / total * 100)) if total > 0 else 100
    filled = int(size * percentage / 100)
    empty = size - filled
    return "🟩" * filled + "⬜" * empty + f" {percentage}%"

def profile_text(user: Dict) -> str:
    nickname = user.get('nickname', 'Неизвестно')
    total_multiplier = get_total_multiplier(user)
    
    text = (
        f"👤 Профиль {nickname}\n\n"
        f"🍌 Бананы: {int(user['bananas'])}\n"
        f"🖱 За клик: {effective_per_click(user)}\n"
        f"⚙️ Пассивно: {user['per_second']} / сек\n"
        f"📊 Общий множитель: {total_multiplier:.1f}×\n"
    )
    
    boosts = []
    
    # Активные бананы
    active_bananas_info = get_active_bananas_info(user)
    for banana_type, banana_multiplier, banana_remaining in active_bananas_info:
        banana_data = get_banana_data(banana_type)
        min_remaining = banana_remaining // 60
        sec_remaining = banana_remaining % 60
        boosts.append(f"{banana_data['name']} ({banana_multiplier}×) - {min_remaining:02d}:{sec_remaining:02d}")
    
    # Ивенты
    if has_active_event(user):
        remaining = int(user.get("event_expires", 0) - time.time())
        if remaining > 0:
            min_remaining = remaining // 60
            sec_remaining = remaining % 60
            multiplier = user.get("event_multiplier", 1.0)
            event_type = user.get("event_type", "")
            boosts.append(f"🎯 {event_type} ({multiplier}×) - {min_remaining:02d}:{sec_remaining:02d}")
    
    if boosts:
        text += "\n⚡ Активные бусты:\n" + "\n".join(f"• {boost}" for boost in boosts) + "\n"
    
    text += f"🔁 Перерождений всего: {user.get('rebirths', 0)}\n"
    
    upgrades = user.get("upgrades", {})
    text += f"\n📊 Улучшения:\n"
    text += f"• Клик: уровень {upgrades.get('click', 0)}\n"
    text += f"• Сборщик: уровень {upgrades.get('collector', 0)}\n"
    
    # Показываем купленные бананы
    banana_counts = {}
    for banana_type in BANANA_TYPES:
        level_key = f"{banana_type}_level"
        banana_counts[banana_type] = upgrades.get(level_key, 0)
    
    text += f"\n🍌 Куплено бананов:\n"
    for banana_type, count in banana_counts.items():
        if count > 0:
            banana_data = BANANA_TYPES[banana_type]
            text += f"• {banana_data['name']}: {count}\n"
    
    return text

def shop_text(user: Dict) -> str:
    upgrades = user.get("upgrades", {})
    
    click_level = upgrades.get("click", 0)
    collector_level = upgrades.get("collector", 0)
    
    click_cost = cost_for_upgrade("click", click_level)
    collector_cost = cost_for_upgrade("collector", collector_level)
    
    return (
        f"🛒 Магазин улучшений\n\n"
        f"💰 Баланс: {int(user['bananas'])} 🍌\n\n"
        f"1️⃣ Улучшить клик (уровень {click_level}) → +1 банан за клик\n"
        f"💵 Стоимость: {click_cost} 🍌\n\n"
        f"2️⃣ Улучшить сборщик (уровень {collector_level}) → +1 банан/сек\n"
        f"💵 Стоимость: {collector_cost} 🍌\n\n"
        f"3️⃣ 🍌 Магазин бананов\n"
        f"💵 Разные бананы с множителями от 1.5× до 30×!\n"
        f"📦 Добавляются в инвентарь, активируются отдельно!"
    )

# Функции для работы с магазином бананов
def banana_shop_text(user: Dict) -> str:
    text = "🛒 Магазин бананов\n\n"
    text += f"💰 Баланс: {int(user['bananas'])} 🍌\n\n"
    
    inventory = user.get("inventory", {})
    upgrades = user.get("upgrades", {})
    
    for banana_type, banana_data in BANANA_TYPES.items():
        level_key = f"{banana_type}_level"
        level = upgrades.get(level_key, 0)
        cost = cost_for_upgrade(banana_type, level)
        in_inventory = inventory.get(banana_type, 0)
        
        text += f"{banana_data['name']} ({banana_data['multiplier']}×)\n"
        text += f"💵 Стоимость: {cost} 🍌\n"
        text += f"📦 В инвентаре: {in_inventory}\n"
        text += f"⏰ Длительность: {banana_data['duration']//60} мин\n"
        text += f"🛒 Куплено: {level}\n\n"
    
    text += "💡 Бананы добавляются в инвентарь и активируются отдельно!"
    return text

def banana_shop_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Добавляем кнопки для каждого типа банана
    for banana_type, banana_data in BANANA_TYPES.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{banana_data['name']} ({banana_data['multiplier']}×)", 
                callback_data=f"buy_banana_{banana_type}"
            )
        ])
    
    # Кнопки навигации
    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="⬅ Назад в магазин", callback_data="shop")]
    ])
    
    return keyboard

def inventory_text(user: Dict) -> str:
    inventory = user.get("inventory", {})
    
    if not inventory:
        return "🎒 Инвентарь пуст\n\nКупи бананы в магазине или получи их за перерождения!"
    
    text = "🎒 Твой инвентарь:\n\n"
    
    # Показываем активные бананы
    active_bananas_info = get_active_bananas_info(user)
    if active_bananas_info:
        text += "⚡ Активные бананы:\n"
        for banana_type, banana_multiplier, banana_remaining in active_bananas_info:
            banana_data = get_banana_data(banana_type)
            min_remaining = banana_remaining // 60
            sec_remaining = banana_remaining % 60
            text += f"• {banana_data['name']} ({banana_multiplier}×) - {min_remaining:02d}:{sec_remaining:02d}\n"
        text += "\n"
    
    # Показываем все бананы в инвентаре
    for banana_type, banana_data in BANANA_TYPES.items():
        count = inventory.get(banana_type, 0)
        if count > 0:
            text += f"{banana_data['name']}: {count} шт.\n"
            text += f"   ⚡ Множитель: {banana_data['multiplier']}×\n"
            text += f"   ⏰ Длительность: {banana_data['duration']//60} мин\n\n"
    
    text += "📦 Используй бананы для усиления кликов!"
    return text

def inventory_keyboard(user: Dict):
    inventory = user.get("inventory", {})
    
    buttons = []
    
    # Кнопки для использования бананов
    for banana_type, banana_data in BANANA_TYPES.items():
        count = inventory.get(banana_type, 0)
        if count > 0:
            buttons.append([InlineKeyboardButton(
                text=f"⚡ Использовать {banana_data['name']} (есть: {count})", 
                callback_data=f"use_banana_{banana_type}"
            )])
    
    buttons.extend([
        [InlineKeyboardButton(text="🛒 Магазин бананов", callback_data="banana_shop")],
        [InlineKeyboardButton(text="⬅ Назад в меню", callback_data="back_to_main")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖱 Улучшить клик", callback_data="buy_click")],
        [InlineKeyboardButton(text="⚙️ Улучшить сборщик", callback_data="buy_collector")],
        [InlineKeyboardButton(text="🍌 Магазин бананов", callback_data="banana_shop")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="⬅ Назад в меню", callback_data="back_to_main")]
    ])

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍌 Кликнуть", callback_data="click"),
         InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton(text="🔁 Перерождение", callback_data="rebirth")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Выдать бананы", callback_data="admin_give_bananas")],
        [InlineKeyboardButton(text="✨ Запустить ивент", callback_data="admin_start_event")],
        [InlineKeyboardButton(text="⏹️ Остановить ивент", callback_data="admin_stop_event")],
        [InlineKeyboardButton(text="👥 Новые регистрации", callback_data="admin_new_users")],
        [InlineKeyboardButton(text="🔄 Сбросить данные", callback_data="admin_reset_data")]
    ])

def admin_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад в админ-панель", callback_data="admin_back")]
    ])

def events_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_data in AVAILABLE_EVENTS.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=event_data["name"], 
                callback_data=f"admin_event_{event_id}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back")
    ])
    return keyboard

def login_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Войти в аккаунт", callback_data="login")],
        [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="register")]
    ])

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ УВЕДОМЛЕНИЙ ==========

async def send_notification_to_user(user_id: int, message: str) -> bool:
    """
    Отправляет уведомление конкретному пользователю.
    Возвращает True если успешно, False если ошибка.
    """
    try:
        from bot_instance import bot
        await bot.send_message(user_id, message)
        return True
    except Exception as e:
        log.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
        return False

async def send_notification_to_all_users(message: str) -> int:
    """
    Отправляет уведомление всем пользователям.
    Возвращает количество успешно уведомленных пользователей.
    """
    try:
        from bot_instance import bot
        users = db.all_users()
        notified_count = 0
        
        for user in users:
            try:
                await bot.send_message(user["user_id"], message)
                notified_count += 1
                # Небольшая задержка чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.1)
            except Exception as e:
                log.warning(f"Не удалось отправить уведомление пользователю {user['user_id']}: {e}")
                continue
        
        return notified_count
    except Exception as e:
        log.error(f"Ошибка при массовой отправке уведомлений: {e}")
        return 0

# ========== РЕГИСТРАЦИЯ И АВТОРИЗАЦИЯ ==========

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    telegram_username = message.from_user.username or "unknown"
    
    # Проверяем, есть ли пользователь в базе
    user = db.get_user(user_id)
    
    if user:
        # Если пользователь уже зарегистрирован, обновляем telegram username
        db.update_user(user_id, telegram_username=telegram_username)
        ensure_and_update_offline(user_id)
        await message.answer(f"👋 С возвращением, {user.get('nickname', 'друг')}!\nНакликай себе бананы!", reply_markup=main_menu_keyboard())
    else:
        # Если пользователя нет, предлагаем войти или зарегистрироваться
        await message.answer(
            "👋 Добро пожаловать в Banana Bot!\n\n"
            "Для игры необходимо иметь аккаунт. Выберите действие:",
            reply_markup=login_keyboard()
        )

@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 Регистрация нового аккаунта\n\n"
        "Придумайте уникальный никнейм для отображения в игре:\n\n"
        "⚠️ Никнейм должен быть уникальным и не повторяться с другими игроками"
    )
    await state.set_state(RegistrationStates.waiting_for_nickname)
    await callback.answer()

@router.message(RegistrationStates.waiting_for_nickname)
async def process_registration_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    
    # Проверяем длину никнейма
    if len(nickname) < 3:
        await message.answer("❌ Никнейм должен содержать минимум 3 символа. Попробуйте еще раз:")
        return
    
    if len(nickname) > 20:
        await message.answer("❌ Никнейм не должен превышать 20 символов. Попробуйте еще раз:")
        return
    
    # Проверяем уникальность никнейма
    if is_nickname_taken(nickname):
        await message.answer("❌ Этот никнейм уже занят. Придумайте другой:")
        return
    
    await state.update_data(nickname=nickname)
    await message.answer(
        f"✅ Никнейм '{nickname}' свободен!\n\n"
        f"Теперь придумайте пароль для вашего аккаунта:\n\n"
        f"⚠️ Пароль должен содержать минимум 6 символов"
    )
    await state.set_state(RegistrationStates.waiting_for_password)

@router.message(RegistrationStates.waiting_for_password)
async def process_registration_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    
    # Проверяем длину пароля
    if len(password) < 6:
        await message.answer("❌ Пароль должен содержать минимум 6 символов. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    nickname = data['nickname']
    
    # Создаем пользователя
    user_id = message.from_user.id
    telegram_username = message.from_user.username or "unknown"
    
    # Хешируем пароль
    hashed_password = hash_password(password)
    
    # Создаем пользователя с новыми полями
    db.create_user_if_not_exists(user_id, telegram_username)
    db.update_user(
        user_id,
        nickname=nickname,
        password_hash=hashed_password,
        telegram_username=telegram_username
    )
    
    # Уведомляем админа о новой регистрации
    try:
        from bot_instance import bot
        await bot.send_message(
            ADMIN_ID,
            f"🆕 Новая регистрация!\n"
            f"👤 Никнейм: {nickname}\n"
            f"📱 Telegram: @{telegram_username}\n"
            f"🆔 ID: {user_id}\n"
            f"🕒 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except:
        pass
    
    await message.answer(
        f"✅ Регистрация успешна!\n\n"
        f"👤 Ваш никнейм: {nickname}\n"
        f"🔐 Пароль: {'*' * len(password)}\n\n"
        f"💡 Запомните эти данные для входа!\n\n"
        f"Теперь ты можешь кликать бананы, улучшать свои возможности и участвовать в ивентах!",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "login")
async def start_login(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔐 Вход в аккаунт\n\n"
        "Введите ваш никнейм:"
    )
    await state.set_state(RegistrationStates.waiting_for_login)
    await callback.answer()

@router.message(RegistrationStates.waiting_for_login)
async def process_login_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    
    # Ищем пользователя по никнейму
    user = get_user_by_nickname(nickname)
    
    if not user:
        await message.answer("❌ Аккаунт с таким никнеймом не найден. Попробуйте еще раз или зарегистрируйтесь:")
        return
    
    await state.update_data(login_nickname=nickname, user_id=user['user_id'])
    await message.answer(f"👤 Найден аккаунт: {nickname}\n\nВведите пароль:")
    await state.set_state(RegistrationStates.waiting_for_password)

# Общий обработчик для пароля при входе
@router.message(RegistrationStates.waiting_for_password)
async def process_login_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    
    if 'login_nickname' in data:
        # Это вход по паролю
        user_id = data['user_id']
        user = db.get_user(user_id)
        
        # Проверяем пароль
        if user.get('password_hash') == hash_password(password):
            # Обновляем telegram username
            telegram_username = message.from_user.username or "unknown"
            db.update_user(user_id, telegram_username=telegram_username)
            
            await message.answer(
                f"✅ Вход выполнен!\n\n"
                f"👋 С возвращением, {user.get('nickname', 'друг')}!",
                reply_markup=main_menu_keyboard()
            )
        else:
            await message.answer("❌ Неверный пароль. Попробуйте еще раз:")
        await state.clear()

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /start для входа или регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id)
    await message.answer(profile_text(user), reply_markup=main_menu_keyboard())

@router.message(Command("shop"))
async def shop_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /start для входа или регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id)
    await message.answer(shop_text(user), reply_markup=shop_keyboard())

@router.message(Command("inventory"))
async def inventory_command(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /start для входа или регистрации.")
        return
        
    user = ensure_and_update_offline(message.from_user.id)
    await message.answer(inventory_text(user), reply_markup=inventory_keyboard(user))

# ========== АДМИН КОМАНДЫ ==========

@router.message(Command("admin"))
async def admin_command(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем права администратора
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    # Проверяем пароль
    if len(message.text.split()) < 2:
        await message.answer("❌ Использование: /admin <пароль>")
        return
    
    password = message.text.split()[1]
    if password != ADMIN_PASSWORD:
        await message.answer("❌ Неверный пароль администратора!")
        return
    
    await message.answer("🛠️ Панель администратора:", reply_markup=admin_keyboard())

# ========== CALLBACK ОБРАБОТЧИКИ ==========

@router.callback_query(F.data == "click")
async def handle_click(callback: CallbackQuery):
    await callback.answer()
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Вы не авторизованы!", show_alert=True)
        return
        
    user = ensure_and_update_offline(callback.from_user.id)
    per_click = effective_per_click(user)
    
    new_bananas = user['bananas'] + per_click
    db.update_user(callback.from_user.id, bananas=new_bananas, last_update=time.time())
    
    user = db.get_user(callback.from_user.id)
    
    # Получаем информацию об активных бустах с оставшимся временем
    boosts_info = []
    
    # Активные бананы
    active_bananas_info = get_active_bananas_info(user)
    for banana_type, banana_multiplier, banana_remaining in active_bananas_info:
        banana_data = get_banana_data(banana_type)
        min_remaining = banana_remaining // 60
        sec_remaining = banana_remaining % 
