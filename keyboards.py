from datetime import datetime as dt
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeDefault
from config import get_user, CROP_GROW_TIMES


async def set_bot_commands(bot, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Устанавливает команды бота с поддержкой повторных попыток и экспоненциального бэкоффа.
    
    Args:
        bot: Экземпляр Bot из aiogram
        max_retries: Максимальное количество повторных попыток (по умолчанию 3)
        initial_delay: Начальная задержка в секундах (по умолчанию 1.0)
    """
    commands = [
        BotCommand(command="farm", description="🌾 На ферму"),
        BotCommand(command="city", description="🚗 В город"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="friends", description="👥 Друзья и соседи"),
        BotCommand(command="shop", description="🏪 Магазин"),
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    
    for attempt in range(max_retries):
        try:
            await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
            print("✅ Команды бота успешно установлены")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Экспоненциальный бэкофф: 1, 2, 4 сек
                print(f"⚠️ Ошибка при установке команд (попытка {attempt + 1}/{max_retries}): {e}")
                print(f"   Повторная попытка через {delay:.1f} сек...")
                await asyncio.sleep(delay)
            else:
                print(f"❌ Не удалось установить команды после {max_retries} попыток: {e}")
                print("   Бот продолжит работу без регистрации команд")
                return False


# ===================== ГЛАВНОЕ МЕНЮ =====================
def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌾 На ферму", callback_data="farm")],
        [InlineKeyboardButton(text="🚗 В город", callback_data="city")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="👥 Друзья и соседи", callback_data="friends")],
        [InlineKeyboardButton(text="🏪 Магазин", callback_data="shop")],
    ])
    return kb


# ===================== ФЕРМА =====================
def farm_kb(user_id: int):
    user = get_user(user_id)
    buttons = []
    for i in range(user["beds"]):
        bed = user["beds_data"][i]
        now = dt.now()
        if bed["crop"] is None:
            # Проверка на заросшую грядку
            last_planted = bed.get("last_planted")
            is_overgrown = False
            if last_planted:
                if isinstance(last_planted, str):
                    try:
                        last_planted = dt.fromisoformat(last_planted)
                    except:
                        last_planted = None
                if last_planted and (now - last_planted).total_seconds() > 12 * 3600:
                    is_overgrown = True

            if is_overgrown:
                text = f"Грядка {i + 1}: 🌿 Заросла - 🧹 Расчистить"
            else:
                text = f"Грядка {i + 1}: пусто🟫"
        elif bed["crop"] and bed["planted_at"]:
            planted = bed["planted_at"]
            if isinstance(planted, str):
                planted = dt.fromisoformat(planted)
            elapsed = (now - planted).total_seconds() / 60
            
            # Исправляем grow_time если он неправильный (миграция для старых данных)
            correct_grow_time = CROP_GROW_TIMES.get(bed["crop"], 1)
            if bed["grow_time"] != correct_grow_time:
                bed["grow_time"] = correct_grow_time
            
            if elapsed >= bed["grow_time"]:
                text = f"Грядка {i + 1}: {bed['crop']} созрела"
            else:
                remain = bed["grow_time"] - elapsed
                if remain < 1:
                    text = f"Грядка {i + 1}: 🌱 {bed['crop']} (<1м)"
                elif remain < 60:
                    text = f"Грядка {i + 1}: 🌱 {bed['crop']} ({int(remain)}м)"
                else:
                    hours = int(remain // 60)
                    mins = int(remain % 60)
                    text = f"Грядка {i + 1}: 🌱 {bed['crop']} ({hours}ч {mins}м)"
        else:
            text = f"Грядка {i + 1}: пусто🟫"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"bed_{i}")])

    if _check_vip(user):
        buttons.append([
            InlineKeyboardButton(text="🌱 Засадить все", callback_data="mass_plant"),
            InlineKeyboardButton(text="🧹 Собрать все", callback_data="mass_harvest")
        ])

    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== ГОРОД =====================
def city_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧔🏻 Председатель СНТ", callback_data="chairman")],
        [InlineKeyboardButton(text="🥬 Овощебаза", callback_data="market")],
        [InlineKeyboardButton(text="📚 Библиотека", callback_data="library")],
        [InlineKeyboardButton(text="👩‍🌾 Доярка Жанна", callback_data="janna")],
        [InlineKeyboardButton(text="⛏️ Шахта", callback_data="mine_enter")],
        [InlineKeyboardButton(text="🎣 Рыбалка", callback_data="fishing_enter")],
        [InlineKeyboardButton(text="🤝 Кооператив", callback_data="coop")],
        [InlineKeyboardButton(text="🌸 Клумба", callback_data="flowerbed")],
        [InlineKeyboardButton(text="🎪 Фестиваль", callback_data="festival")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")],
    ])
    return kb


# ===================== ПРОФИЛЬ =====================
def profile_kb(user_id: int):
    user = get_user(user_id)
    buttons = []

    level = user.get("level", 1)
    reward_key = f"level_reward_{level}"
    if user.get(reward_key):
        buttons.append([InlineKeyboardButton(text="❌ Награда за уровень получена", callback_data="noop")])
    else:
        reward_text = _get_level_reward_text(level)
        buttons.append([InlineKeyboardButton(text=f"🎁 Награда {level}ур: {reward_text}",
                                             callback_data=f"claim_level_reward_{level}")])

    buttons.append([InlineKeyboardButton(text="✏️ Изменить имя (50000💰)", callback_data="change_name")])

    if _check_vip(user):
        buttons.append([InlineKeyboardButton(text="👑 Управление VIP", callback_data="manage_vip")])
    else:
        buttons.append([InlineKeyboardButton(text="👑 Стать VIP", callback_data="become_vip")])

    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _get_level_reward_text(level: int):
    rewards = {
        1: "🧅 5 семян лука",
        2: "🥔 5 семян картофеля + ⭐3",
        3: "🌾 5 семян пшеницы + ⭐5",
        4: "🍓 5 семян клубники + ⭐7",
        5: "🎫 3 билета + ⭐10",
        6: "🌽 5 семян кукурузы + ⭐12",
        7: "🍇 5 семян винограда + ⭐15",
        8: "🍚 5 семян риса + ⭐18",
        9: "🎃 5 семян тыквы + ⭐20",
        10: "📄 1 чертеж + ⭐25 + 🎫5",
    }
    return rewards.get(level, "⭐ 5 звёзд")


# ===================== ПРЕДСЕДАТЕЛЬ СНТ =====================
def chairman_kb(user_id: int):
    user = get_user(user_id)
    permit_text = "📝 Подать заявление"

    if user.get("permit_pending"):
        pending = user["permit_pending"]
        if isinstance(pending, str):
            try:
                pending = dt.fromisoformat(pending)
            except:
                pending = None
        if pending and pending > dt.now():
            remaining = pending - dt.now()
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            permit_text = f"⏳ Проверка ({hours}ч {mins}м)"

    if user.get("permit_ready"):
        permit_text = "✅ Забрать разрешение"

    buttons = [
        [InlineKeyboardButton(text=permit_text, callback_data="permit_apply")],
        [InlineKeyboardButton(text="🚔 Нанять ЧОП", callback_data="chop_hire")],
        [InlineKeyboardButton(text="📦 Доставки", callback_data="deliveries")],
        [InlineKeyboardButton(text="👵🏼 Завхоз СНТ", callback_data="zavhoz")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== БИБЛИОТЕКА =====================
def library_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛️ Музей", callback_data="museum")],
        [InlineKeyboardButton(text="🌱 Растения", callback_data="lib_plants")],
        [InlineKeyboardButton(text="🌳 Деревья", callback_data="lib_trees")],
        [InlineKeyboardButton(text="🏠 Строения", callback_data="lib_buildings")],
        [InlineKeyboardButton(text="🐄 Животные", callback_data="lib_animals")],
        [InlineKeyboardButton(text="🎮 Механики игры", callback_data="lib_mechanics")],
        [InlineKeyboardButton(text="🎰 Колесо Жанны", callback_data="lib_wheel")],
        [InlineKeyboardButton(text="⛏️ Шахта", callback_data="lib_mine")],
        [InlineKeyboardButton(text="🎣 Рыбалка", callback_data="lib_fishing")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")]
    ])
    return kb


# ===================== ВСПОМОГАТЕЛЬНЫЕ =====================
def _check_vip(user):
    vip_until = user.get("vip_until")
    if vip_until:
        if isinstance(vip_until, str):
            try:
                vip_until = dt.fromisoformat(vip_until)
            except:
                return False
        if vip_until > dt.now():
            return True
    return False