from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user
from handlers_museum import router as museum_router

router = Router()
router.include_router(museum_router)


def library_main_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛️ Музей 🏛️", callback_data="museum")],
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


def buildings_list_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚒️ Кузница", callback_data="lib_build_smithy")],
        [InlineKeyboardButton(text="🍞 Булочная", callback_data="lib_build_bakery")],
        [InlineKeyboardButton(text="🥛 Жирмолкомбинат", callback_data="lib_build_dairy")],
        [InlineKeyboardButton(text="🍰 Кондитерская", callback_data="lib_build_confectionery")],
        [InlineKeyboardButton(text="🥃 Винокурня", callback_data="lib_build_distillery")],
        [InlineKeyboardButton(text="🥜 Кормоцех", callback_data="lib_build_feedmill")],
        [InlineKeyboardButton(text="🍳 Кухня", callback_data="lib_build_kitchen")],
        [InlineKeyboardButton(text="🧵 Ткацкий цех", callback_data="lib_build_textile")],
        [InlineKeyboardButton(text="🐟 Рыбный цех", callback_data="lib_build_fish")],
        [InlineKeyboardButton(text="⭐ Фабрика звёзд", callback_data="lib_build_starfactory")],
        [InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")],
        [InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")]
    ])
    return kb


def read_reward_kb(section: str, already_read: bool):
    buttons = []
    if not already_read:
        buttons.append([InlineKeyboardButton(text="⭐ Я прочел (5 звезд)!", callback_data=f"read_{section}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Уже прочитано (5⭐ получено)", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в библиотеку", callback_data="library")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "library")
async def library_main(call: types.CallbackQuery):
    await call.message.edit_text(
        "📚 Библиотека\n\n"
        "Добро пожаловать в нашу библиотеку! Здесь вы можете узнать больше о растениях, "
        "животных и других аспектах игры.\n\n"
        "Выберите интересующий вас раздел:",
        reply_markup=library_main_kb()
    )


# ---------- 🌱 Растения ----------
@router.callback_query(F.data == "lib_plants")
async def lib_plants(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_plants", False)
    text = (
        "📚 Библиотека фермера | 🌱 Растения\n\n"
        "🌱 Информация о растениях:\n\n"
        "⭐️ Обычные / Премиум растения ⭐️\n\n"
        "🥕 Морковь / 🧅 Лук\n⏰ 1 мин / 1 мин\n💰 1 / 1 монет\n📦 4 / 8\n🔹 1 / 5\n\n"
        "🥔 Картофель / 🥦 Капуста\n⏰ 10 мин / 8 мин\n💰 5 / 5\n📦 6 / 8\n🔹 15 / 15\n\n"
        "🌾 Пшеница / 🌽 Кукуруза\n⏰ 1 ч / 50 мин\n💰 20 / 20\n📦 10 / 12\n🔹 30 / 30\n\n"
        "🍓 Клубника / 🍇 Виноград\n⏰ 5 ч / 4 ч\n💰 100 / 100\n📦 12 / 14\n🔹 100 / 100\n\n"
        "🍚 Рис / 🍠 Батат\n⏰ 12 ч / 10 ч\n💰 150 / 150\n📦 14 / 16\n🔹 150 / 150\n\n"
        "🎃 Тыква / 🍆 Баклажан\n⏰ 24 ч / 20 ч\n💰 300 / 300\n📦 16 / 18\n🔹 300 / 300\n\n"
        "💩 Удобрения: увеличивают урожай в 1.5 раза"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_plants", already_read))


# ---------- 🌳 Деревья ----------
@router.callback_query(F.data == "lib_trees")
async def lib_trees(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_trees", False)
    text = (
        "📚 Библиотека фермера | 🌳 Деревья\n\n"
        "🌳 Информация о деревьях:\n\n"
        "🌳 Яблоня 🍎\n🌱 Рост саженца: 7 дней\n🍎 Созревание плодов: 24 ч\n"
        "💰 Цена продажи: 200 монет\n📦 Количество за сбор: 20\n🔹 Опыт за сбор: 400\n\n"
        "🌴 Пальма 🍌\n🌱 Рост саженца: 6 дней\n🍎 Созревание плодов: 20 ч\n"
        "💰 Цена продажи: 200 монет\n📦 Количество за сбор: 22\n🔹 Опыт за сбор: 400"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_trees", already_read))


# ---------- 🏠 Строения ----------
@router.callback_query(F.data == "lib_buildings")
async def lib_buildings(call: types.CallbackQuery):
    text = (
        "📚 Библиотека фермера | 🏭 Производственные здания\n\n"
        "Выберите здание для получения подробной информации:"
    )
    await call.message.edit_text(text, reply_markup=buildings_list_kb())


# Заглушки для зданий (можно дополнить позже)
for build_name in ["smithy", "bakery", "dairy", "confectionery", "distillery", "feedmill", "kitchen", "textile", "fish",
                   "starfactory"]:
    @router.callback_query(F.data == f"lib_build_{build_name}")
    async def lib_build_generic(call: types.CallbackQuery, name=build_name):
        user = get_user(call.from_user.id)
        already_read = user.get(f"read_lib_build_{name}", False)
        await call.message.edit_text(
            f"📚 Информация о здании «{name}»\n\nСкоро будет дополнено...",
            reply_markup=read_reward_kb(f"lib_build_{name}", already_read)
        )


# ---------- 🐄 Животные ----------
@router.callback_query(F.data == "lib_animals")
async def lib_animals(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_animals", False)
    text = (
        "📚 Библиотека фермера | 🐄 Животные\n\n"
        "🐓 Курица: 🥚 Яйца, ⏰ 12ч, 🌿 1 корма, 💰 100\n"
        "🐏 Овца: 🧶 Шерсть, ⏰ 12ч, 🌿 2 корма, 💰 150\n"
        "🐄 Корова: 🥛 Молоко, ⏰ 12ч, 🌿 3 корма, 💰 200\n"
        "🐖 Хрюшка: 🍄 Грибы, ⏰ 24ч, 🌿 4 корма, 💰 250"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_animals", already_read))


# ---------- 🎮 Механики ----------
@router.callback_query(F.data == "lib_mechanics")
async def lib_mechanics(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_mechanics", False)
    text = (
        "📚 Библиотека фермера | 🎮 Механики игры\n\n"
        "📈 Система уровней: Получайте опыт за сбор урожая\n"
        "⭐ Звезды: Премиум валюта, 1⭐ = 1 час ускорения\n"
        "👨‍💼 Председатель СНТ: Выдаёт разрешения, нанимает ЧОП\n"
        "📋 Задания: От Завхоза СНТ и Доярки Жанны\n"
        "🏛️ Музей: Сдавайте урожай за награды"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_mechanics", already_read))


# ---------- 🎰 Колесо Жанны ----------
@router.callback_query(F.data == "lib_wheel")
async def lib_wheel(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_wheel", False)
    text = (
        "📚 Библиотека фермера | 🎰 Колесо Жанны\n\n"
        "🎰 О Колесе Жанны:\n"
        "• Игра на удачу с ценными призами\n"
        "• Стоимость: 1 🎫 билет удачи\n"
        "• 64 различных комбинации = 64 разных приза\n\n"
        "🎁 Призы: семена вишни, лимона, маргаритки, звёзды, удобрения, разрешения"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_wheel", already_read))


# ---------- ⛏️ Шахта ----------
@router.callback_query(F.data == "lib_mine")
async def lib_mine(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_mine", False)
    text = (
        "📚 Библиотека фермера | ⛏️ Шахта\n\n"
        "⛏️ О шахте:\n"
        "• Доступна с 5 уровня\n"
        "• Для входа нужна 1 тяпка ⛏️\n"
        "• 15 этажей различной сложности\n"
        "• Враги: летучие мыши, крысы, пауки, змеи, гоблины, скелеты, тролли, демоны, драконы\n"
        "• Ресурсы: камень, железо, чертежи, монеты"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_mine", already_read))


# ---------- 🎣 Рыбалка ----------
@router.callback_query(F.data == "lib_fishing")
async def lib_fishing(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    already_read = user.get("read_lib_fishing", False)
    text = (
        "📚 Библиотека фермера | 🎣 Рыбалка\n\n"
        "🎣 О рыбалке:\n"
        "• Мини-игра на озере\n"
        "• Доступна с 5 уровня\n"
        "• Для начала нужен 1 🪱 червяк\n"
        "• Бросаете 3 дротика 🎯 (значения 1-6)\n"
        "• Рыбы: Фугу, Креветка, Карась, Окунь, Щука, Белуга\n"
        "• Три одинаковых — экипировка!"
    )
    await call.message.edit_text(text, reply_markup=read_reward_kb("lib_fishing", already_read))


# ---------- Обработчик начисления звёзд за чтение ----------
@router.callback_query(F.data.startswith("read_"))
async def read_section(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    section = call.data.replace("read_", "")

    # Проверка, получал ли уже награду за этот раздел
    read_key = f"read_{section}"
    if user.get(read_key):
        await call.answer("Вы уже получили награду за этот раздел!")
        return

    user[read_key] = True
    user["stars"] = user.get("stars", 0) + 5
    await call.answer("Получено 5⭐!")

    # Возвращаем в библиотеку
    await library_main(call)


@router.callback_query(F.data == "noop")
async def noop(call: types.CallbackQuery):
    await call.answer("Ничего не происходит")