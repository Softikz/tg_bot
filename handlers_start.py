from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user
from keyboards import farm_kb, main_menu_kb

router = Router()


class Tutorial(StatesGroup):
    waiting_name = State()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
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


@router.callback_query(F.data == "tutorial_start")
async def tutorial_step1(call: types.CallbackQuery, state: FSMContext):
    user = get_user(call.from_user.id)
    user["seeds"] = {"🥕": 10}

    await call.message.edit_text(
        "Пиги: Отлично! Давай посадим твой первый урожай! 🌱\n"
        "У тебя уже есть 10 семян моркови 🥕\n"
        "Нажми на кнопку «Грядка 1: 🟫 Пусто» ниже и выбери семена моркови для посадки!",
        reply_markup=None
    )
    await call.message.answer(
        "🌱 Ваша ферма, нажмите на грядку чтобы посадить или собрать урожай",
        reply_markup=farm_kb(call.from_user.id)
    )
    await state.set_state(Tutorial.waiting_name)