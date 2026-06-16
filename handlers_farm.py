import asyncio
import random
from datetime import datetime
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, CROP_GROW_TIMES, CROP_YIELDS, CROP_EXP, TITLES
from keyboards import farm_kb, main_menu_kb
from handlers_deliveries import update_quest_progress
from handlers_janna import update_daily_task_progress

router = Router()


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(call: types.CallbackQuery):
    await call.message.edit_text(
        "👋 Добро пожаловать на Ферму!\n\n"
        "Используйте кнопки внизу для навигации:\n\n"
        "• 🌱 Кликайте на грядку, чтобы сажать семена\n"
        "• 🍒 Продавайте урожай на овощебазе в городе\n"
        "• 🌿 Расширяйте грядки и изучайте новые культуры\n"
        "• 🙌 Посещайте соседей и заводите новых друзей",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "farm")
async def farm_view(call: types.CallbackQuery):
    await call.message.edit_text(
        "🌱 Ваша ферма, нажмите на грядку чтобы посадить или собрать урожай",
        reply_markup=farm_kb(call.from_user.id)
    )


@router.callback_query(F.data.startswith("bed_"))
async def bed_click(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    bed_idx = int(call.data.split("_")[1])

    if bed_idx >= len(user["beds_data"]):
        await call.answer("Грядка не найдена")
        return

    bed = user["beds_data"][bed_idx]
    now = datetime.now()

    # Если на грядке что-то растёт
    if bed["crop"] and bed["planted_at"]:
        planted = bed["planted_at"]
        if isinstance(planted, str):
            try:
                planted = datetime.fromisoformat(planted)
            except:
                planted = now

        elapsed = (now - planted).total_seconds() / 60
        
        # Исправляем grow_time если он неправильный (миграция для старых данных)
        correct_grow_time = CROP_GROW_TIMES.get(bed["crop"], 1)
        if bed["grow_time"] != correct_grow_time:
            bed["grow_time"] = correct_grow_time

        if elapsed >= bed["grow_time"]:
            # Сбор урожая
            crop = bed["crop"]
            amount = CROP_YIELDS.get(crop, 4)
            exp = CROP_EXP.get(crop, 1)

            if user["harvest"].get("💩 Удобрение", 0) > 0:
                user["harvest"]["💩 Удобрение"] -= 1
                amount = int(amount * 1.5)

            user["harvest"][crop] = user["harvest"].get(crop, 0) + amount
            user["exp"] = user.get("exp", 0) + exp

            bed["crop"] = None
            bed["planted_at"] = None
            bed["last_planted"] = now

            if bed_idx in user.get("chop_guarded", []):
                user["chop_guarded"].remove(bed_idx)

            # Обновление квестов
            update_quest_progress(call.from_user.id, "harvest", 1)
            update_daily_task_progress(call.from_user.id, "harvest", 1)

            await call.message.edit_text(
                f"✅ Вы собрали {crop} ({amount}шт)!\n\n+{exp} опыта",
                reply_markup=farm_kb(call.from_user.id)
            )

            check_level_up(call.from_user.id, call.bot)

            if not user.get("tutorial_complete"):
                user["tutorial_complete"] = True
                await call.message.answer(
                    "Пиги: Молодец! Первый урожай собран! 🎉\n\n"
                    "Теперь у тебя есть морковь. Её можно продать на Овощебазе и получить монеты!\n\n"
                    "Нажми на кнопку 🚗 внизу экрана, чтобы поехать в город!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚗 Город", callback_data="city")]
                    ])
                )
            return
        else:
            remain = bed["grow_time"] - elapsed
            if remain < 1:
                await call.answer("🌱 Почти выросло!")
            elif remain < 60:
                await call.answer(f"🌱 Растёт! Осталось {int(remain)}м")
            else:
                hours = int(remain // 60)
                mins = int(remain % 60)
                await call.answer(f"🌱 Растёт! Осталось {hours}ч {mins}м")
            return
    else:
        # Проверка на заросшую грядку
        last_planted = bed.get("last_planted")
        is_overgrown = False
        if last_planted:
            if isinstance(last_planted, str):
                try:
                    last_planted = datetime.fromisoformat(last_planted)
                except:
                    last_planted = None
            if last_planted and (now - last_planted).total_seconds() > 12 * 3600:
                is_overgrown = True

        if is_overgrown:
            await call.message.edit_text(
                f"🌿 Грядка {bed_idx + 1} заросла!\n\n"
                "Нажмите кнопку ниже чтобы расчистить её и получить силос.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🧹 Расчистить (🌿 силос)", callback_data=f"clear_bed_{bed_idx}")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="farm")]
                ])
            )
            return

        # Посадка — грядка пуста
        seeds = user.get("seeds", {})
        available_seeds = {crop: cnt for crop, cnt in seeds.items() if cnt > 0}

        if not available_seeds:
            await call.answer("Нет семян! Купите в магазине 🏪")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{crop} Семена ({cnt}шт) — {CROP_GROW_TIMES.get(crop, 1)}мин",
                    callback_data=f"plant_{bed_idx}_{crop}"
                )
            ]
            for crop, cnt in available_seeds.items()
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="farm")])

        await call.message.edit_text(
            "🌱 Грядка пуста.\n\nВыберите семена для посадки:",
            reply_markup=kb
        )


@router.callback_query(F.data.startswith("clear_bed_"))
async def clear_bed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    bed_idx = int(call.data.replace("clear_bed_", ""))
    bed = user["beds_data"][bed_idx]

    bed["crop"] = None
    bed["planted_at"] = None
    bed["last_planted"] = None

    silos = random.randint(2, 5)
    user["harvest"]["🌿 Силос"] = user["harvest"].get("🌿 Силос", 0) + silos
    user["exp"] = user.get("exp", 0) + 10

    update_daily_task_progress(call.from_user.id, "clear", 1)

    await call.message.edit_text(
        f"🧹 Грядка {bed_idx + 1} расчищена!\n\n"
        f"🌿 Получено силоса: +{silos}\n"
        f"🔹 Опыт: +10",
        reply_markup=farm_kb(call.from_user.id)
    )


@router.callback_query(F.data.startswith("plant_"))
async def plant_seed(call: types.CallbackQuery):
    parts = call.data.split("_")
    bed_idx = int(parts[1])
    crop = parts[2]
    user = get_user(call.from_user.id)

    if user["seeds"].get(crop, 0) <= 0:
        await call.answer("Нет семян!")
        return

    user["seeds"][crop] -= 1
    grow_time = CROP_GROW_TIMES.get(crop, 1)
    user["beds_data"][bed_idx]["crop"] = crop
    user["beds_data"][bed_idx]["planted_at"] = datetime.now()
    user["beds_data"][bed_idx]["grow_time"] = grow_time

    await call.message.edit_text(
        "🌱 Ваша ферма, нажмите на грядку чтобы посадить или собрать урожай",
        reply_markup=farm_kb(call.from_user.id)
    )

    update_quest_progress(call.from_user.id, "plant_variety", 1)
    update_daily_task_progress(call.from_user.id, "plant_variety", 1)

    if not user.get("tutorial_complete"):
        planted_count = sum(1 for bed in user["beds_data"] if bed["crop"] is not None)
        if planted_count == 1:
            await call.message.answer(
                f"Пиги: Семена посажены! 🌱\n"
                f"Не забудь засеять вторую грядку!\n"
                f"Ждем, морковка растет {grow_time} минут. Я дам знать, когда собирать! ⏳"
            )

    asyncio.create_task(schedule_harvest_notification(call.bot, call.from_user.id, bed_idx, crop, grow_time))


async def schedule_harvest_notification(bot: Bot, user_id: int, bed_idx: int, crop: str, grow_minutes: int):
    await asyncio.sleep(grow_minutes * 60)
    user = get_user(user_id)

    if bed_idx >= len(user["beds_data"]):
        return

    bed = user["beds_data"][bed_idx]
    if bed["crop"] == crop and bed["planted_at"]:
        planted = bed["planted_at"]
        if isinstance(planted, str):
            try:
                planted = datetime.fromisoformat(planted)
            except:
                return
        elapsed = (datetime.now() - planted).total_seconds() / 60
        if elapsed >= grow_minutes:
            try:
                await bot.send_message(
                    user_id,
                    f"📬 У вас есть новости!\n\n"
                    f"Ваш урожай готов к сбору!\n\n"
                    f"На грядке {bed_idx + 1} созрела {crop}!\n\n"
                    f"Соберите урожай пока его не украли соседи!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🌾 На ферму", callback_data="farm")]
                    ])
                )

                if not user.get("tutorial_complete"):
                    await bot.send_message(
                        user_id,
                        f"Пиги: Ура! Твой первый урожай созрел!{crop}\n\n"
                        "Скорее нажми на грядку с морковкой, чтобы собрать урожай!",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🌾 На ферму", callback_data="farm")]
                        ])
                    )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")


@router.callback_query(F.data == "mass_plant")
async def mass_plant(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    is_vip = _check_vip(user)

    if not is_vip:
        await call.answer("Только для VIP! 👑")
        return

    seeds = user.get("seeds", {})
    available_seeds = [(crop, cnt) for crop, cnt in seeds.items() if cnt > 0]
    if not available_seeds:
        await call.answer("Нет семян!")
        return

    buttons = []
    for crop, cnt in available_seeds:
        grow_time = CROP_GROW_TIMES.get(crop, 1)
        if grow_time < 60:
            time_text = f"{grow_time}мин"
        else:
            hours = grow_time // 60
            mins = grow_time % 60
            time_text = f"{hours}ч {mins}м" if mins > 0 else f"{hours}ч"
        buttons.append([InlineKeyboardButton(
            text=f"{crop} — {cnt}шт (⏰{time_text})",
            callback_data=f"mass_plant_{crop}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="farm")])

    await call.message.edit_text(
        "🌱 Массовая посадка\n\nВыберите культуру для засадки всех пустых грядок:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("mass_plant_"))
async def mass_plant_execute(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    crop = call.data.replace("mass_plant_", "")

    grow_time = CROP_GROW_TIMES.get(crop, 1)
    planted_count = 0

    for i in range(user["beds"]):
        if user["beds_data"][i]["crop"] is None and user["seeds"].get(crop, 0) > 0:
            user["beds_data"][i]["crop"] = crop
            user["beds_data"][i]["planted_at"] = datetime.now()
            user["beds_data"][i]["grow_time"] = grow_time
            user["seeds"][crop] -= 1
            planted_count += 1
            update_daily_task_progress(call.from_user.id, "plant_variety", 1)
            asyncio.create_task(schedule_harvest_notification(call.bot, call.from_user.id, i, crop, grow_time))

    if planted_count > 0:
        await call.message.edit_text(
            f"🌱 Засажено {planted_count} грядок культурой {crop}!",
            reply_markup=farm_kb(call.from_user.id)
        )
    else:
        await call.answer("Нет пустых грядок или недостаточно семян!")


@router.callback_query(F.data == "mass_harvest")
async def mass_harvest(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    is_vip = _check_vip(user)

    if not is_vip:
        await call.answer("Только для VIP! 👑")
        return

    now = datetime.now()
    harvested = 0
    total_exp = 0

    for i in range(user["beds"]):
        bed = user["beds_data"][i]
        if bed["crop"] and bed["planted_at"]:
            planted = bed["planted_at"]
            if isinstance(planted, str):
                try:
                    planted = datetime.fromisoformat(planted)
                except:
                    continue
            elapsed = (now - planted).total_seconds() / 60
            
            # Исправляем grow_time если он неправильный (миграция для старых данных)
            correct_grow_time = CROP_GROW_TIMES.get(bed["crop"], 1)
            if bed["grow_time"] != correct_grow_time:
                bed["grow_time"] = correct_grow_time
            
            if elapsed >= bed["grow_time"]:
                crop = bed["crop"]
                amount = CROP_YIELDS.get(crop, 4)
                exp = CROP_EXP.get(crop, 1)
                user["harvest"][crop] = user["harvest"].get(crop, 0) + amount
                total_exp += exp
                bed["crop"] = None
                bed["planted_at"] = None
                bed["last_planted"] = now
                if i in user.get("chop_guarded", []):
                    user["chop_guarded"].remove(i)
                update_quest_progress(call.from_user.id, "harvest", 1)
                update_daily_task_progress(call.from_user.id, "harvest", 1)
                harvested += 1

    if harvested > 0:
        user["exp"] = user.get("exp", 0) + total_exp
        check_level_up(call.from_user.id, call.bot)
        await call.message.edit_text(
            f"🧹 Собрано {harvested} грядок!\n🔹 Опыт: +{total_exp}",
            reply_markup=farm_kb(call.from_user.id)
        )
    else:
        await call.answer("Нет созревших грядок!")


def _check_vip(user):
    vip_until = user.get("vip_until")
    if vip_until:
        if isinstance(vip_until, str):
            try:
                vip_until = datetime.fromisoformat(vip_until)
            except:
                return False
        if vip_until > datetime.now():
            return True
    return False


def check_level_up(user_id: int, bot: Bot = None):
    user = get_user(user_id)
    level = user.get("level", 1)
    exp_needed = 100 * level

    while user.get("exp", 0) >= exp_needed:
        user["exp"] -= exp_needed
        user["level"] = user.get("level", 1) + 1
        level = user["level"]
        exp_needed = 100 * level

        if level <= len(TITLES):
            user["title"] = TITLES[level - 1]

        if bot:
            async def send_level_up():
                try:
                    await bot.send_message(
                        user_id,
                        f"🎉 Поздравляем! Вы достигли {level} уровня!\n"
                        f"⭐ Новый титул: {user['title']}\n\n"
                        f"Зайдите в Профиль чтобы получить награду за уровень!"
                    )
                except:
                    pass

            asyncio.create_task(send_level_up())