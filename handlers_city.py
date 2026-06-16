from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, CROP_SELL_PRICE, CHOP_PRICE_PER_BED, PERMISSION_TIME
from keyboards import city_kb, chairman_kb
from handlers_deliveries import update_quest_progress
import asyncio
from datetime import datetime, timedelta

router = Router()


@router.callback_query(F.data == "city")
async def city_view(call: types.CallbackQuery):
    await call.message.edit_text(
        "🌃 Город\n\nЗдесь вы можете взаимодействовать с городскими учреждениями, выполнять задания",
        reply_markup=city_kb()
    )


# ==================== ОВОЩЕБАЗА ====================
@router.callback_query(F.data == "market")
async def market(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    has_items = False
    for crop, amount in user["harvest"].items():
        if amount > 0 and crop in CROP_SELL_PRICE:
            has_items = True
            kb.inline_keyboard.append([InlineKeyboardButton(
                text=f"{crop} — {amount} шт. (по {CROP_SELL_PRICE[crop]}💰)",
                callback_data=f"sell_confirm_{crop}"
            )])

    if not has_items:
        kb.inline_keyboard.append([InlineKeyboardButton(text="У вас нет урожая для продажи", callback_data="noop")])

    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад в город", callback_data="city")])
    await call.message.edit_text("🥬 Овощебаза\n\nВыберите товар для продажи:", reply_markup=kb)


@router.callback_query(F.data.startswith("sell_confirm_"))
async def sell_confirm(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    crop = call.data.replace("sell_confirm_", "")
    amount = user["harvest"].get(crop, 0)

    if amount == 0:
        await call.answer("Нет товара")
        return

    price = CROP_SELL_PRICE.get(crop, 1)
    total = price * amount

    await call.message.edit_text(
        f"🥬 Продажа урожая\n\n"
        f"Вы уверены, что хотите продать {crop}?\n"
        f"Количество: {amount} шт.\n"
        f"Цена за шт: {price}💰\n"
        f"Общая сумма: {total}💰",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Да, продать за {total}💰", callback_data=f"sell_{crop}")],
            [InlineKeyboardButton(text="❌ Нет, вернуться", callback_data="market")]
        ])
    )


@router.callback_query(F.data.startswith("sell_"))
async def sell_crop(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    crop = call.data[5:]
    amount = user["harvest"].get(crop, 0)

    if amount == 0:
        await call.answer("Нет товара")
        return

    price = CROP_SELL_PRICE.get(crop, 1)
    total = price * amount
    user["money"] = user.get("money", 0) + total
    user["harvest"][crop] = 0

    # Обновление квестов
    update_quest_progress(call.from_user.id, "sell", amount)
    update_quest_progress(call.from_user.id, "earn", total)

    await call.message.edit_text(
        f"✅ Продано!\n\n{crop} x{amount}\n💰 Получено: {total} монет",
        reply_markup=city_kb()
    )


# ==================== ПРЕДСЕДАТЕЛЬ СНТ ====================
@router.callback_query(F.data == "chairman")
async def chairman_main(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if user.get("permit_ready"):
        user["permissions"] = user.get("permissions", 0) + 1
        user["permit_ready"] = False
        await call.message.edit_text(
            f"🧔🏻 Председатель СНТ\n\n"
            f"✅ Разрешение успешно получено!\n"
            f"Вы получили +1 разрешение.\n"
            f"Текущее количество разрешений: {user['permissions']}",
            reply_markup=chairman_kb(call.from_user.id)
        )
    else:
        await call.message.edit_text(
            "🧔🏻 Председатель СНТ\n\n"
            "Добро пожаловать! Вы можете подать заявление на получение разрешения "
            "для сбора урожая с участков ваших соседей. Процесс оформления занимает около 8 часов.\n\n"
            "🚔 ЧОП \"Безопасный урожай\"\n"
            "Вы можете нанять охрану для защиты вашего урожая от воров. "
            "Стоимость охраны: 2 звезды за грядку до сбора урожая.",
            reply_markup=chairman_kb(call.from_user.id)
        )


@router.callback_query(F.data == "permit_apply")
async def permit_apply(call: types.CallbackQuery):
    user = get_user(call.from_user.id)

    if user.get("permit_ready"):
        user["permissions"] = user.get("permissions", 0) + 1
        user["permit_ready"] = False
        await call.message.edit_text(
            f"🧔🏻 Председатель СНТ\n\n"
            f"✅ Разрешение успешно получено!\n"
            f"Вы получили +1 разрешение.\n"
            f"Текущее количество разрешений: {user['permissions']}",
            reply_markup=chairman_kb(call.from_user.id)
        )
        return

    if user.get("permit_pending"):
        pending = user["permit_pending"]
        if isinstance(pending, str):
            pending = datetime.fromisoformat(pending)
        if pending > datetime.now():
            remaining = pending - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            cost = hours + 1
            await call.message.edit_text(
                f"🧔🏻 Председатель СНТ\n\n"
                f"Ваше заявление рассматривается.\n"
                f"⏳ Осталось времени: {hours}ч {mins}мин.\n"
                f"⭐ Стоимость ускорения: {cost} звёзд\n"
                f"⭐ У вас звёзд: {user.get('stars', 0)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"⚡ Ускорить за {cost}⭐", callback_data="speed_permit")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="chairman")]
                ])
            )
            return

    user["permit_pending"] = datetime.now() + PERMISSION_TIME
    await call.message.edit_text(
        "🧔🏻 Председатель СНТ\n\n"
        "Ваше заявление принято на рассмотрение.\n"
        f"Текущее количество разрешений: {user.get('permissions', 0)}\n"
        f"Время рассмотрения: 8ч. 0 мин.",
        reply_markup=chairman_kb(call.from_user.id)
    )
    asyncio.create_task(permit_ready_notification(call.from_user.id))


async def permit_ready_notification(user_id: int):
    await asyncio.sleep(PERMISSION_TIME.total_seconds())
    user = get_user(user_id)
    if user.get("permit_pending"):
        pending = user["permit_pending"]
        if isinstance(pending, str):
            pending = datetime.fromisoformat(pending)
        if pending <= datetime.now():
            user["permit_pending"] = None
            user["permit_ready"] = True
            try:
                from config import bot
                await bot.send_message(
                    user_id,
                    "📬 У вас есть новости!\n\n"
                    "📝 Ваше разрешение готово! 📝\n\n"
                    "Ваше разрешение на \"сбор\" урожая готово к получению!\n"
                    "Получите его у председателя СНТ.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🧔🏻 К Председателю", callback_data="chairman")]
                    ])
                )
            except:
                pass


@router.callback_query(F.data == "speed_permit")
async def speed_permit(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user.get("permit_pending"):
        await call.answer("Нечего ускорять")
        return

    pending = user["permit_pending"]
    if isinstance(pending, str):
        pending = datetime.fromisoformat(pending)
    if pending <= datetime.now():
        await call.answer("Разрешение уже готово!")
        return

    remaining = (pending - datetime.now()).total_seconds()
    cost = int(remaining // 3600) + 1
    if user.get("stars", 0) < cost:
        await call.answer(f"Недостаточно звёзд! Нужно {cost}⭐")
        return

    user["stars"] -= cost
    user["permit_pending"] = None
    user["permit_ready"] = True
    user["permissions"] = user.get("permissions", 0) + 1
    user["permit_ready"] = False

    await call.message.edit_text(
        f"🧔🏻 Председатель СНТ\n\n"
        f"✅ Разрешение успешно получено!\n"
        f"Вы получили +1 разрешение.\n"
        f"Текущее количество разрешений: {user['permissions']}",
        reply_markup=chairman_kb(call.from_user.id)
    )


@router.callback_query(F.data == "chop_hire")
async def chop_hire(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    buttons = []
    for i in range(user["beds"]):
        bed = user["beds_data"][i]
        if bed["crop"]:
            text = f"Грядка {i + 1}: {bed['crop']}"
        else:
            text = f"Грядка {i + 1}: пусто"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"chop_guard_{i}")])

    total_cost = user["beds"] * CHOP_PRICE_PER_BED
    buttons.append([InlineKeyboardButton(text=f"🚔 Охранять все ({total_cost}⭐)", callback_data="chop_all")])
    buttons.append([InlineKeyboardButton(text="🧔🏻 Назад к председателю", callback_data="chairman")])

    await call.message.edit_text(
        f"🚔 Найм ЧОП\n\n"
        f"Охранники готовы за звёзды охранять ваши грядки до следующего сбора урожая.\n"
        f"Охраняемые грядки не смогут быть украдены другими игроками.\n"
        f"Стоимость: 2⭐ за 1 грядку.\n"
        f"У вас есть: {user.get('stars', 0)}⭐\n\n"
        f"Выберите грядку, которую хотите поставить под охрану:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("chop_guard_"))
async def chop_guard_bed(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    bed_idx = int(call.data.split("_")[2])

    if user.get("stars", 0) < CHOP_PRICE_PER_BED:
        await call.answer(f"Недостаточно звёзд! Нужно {CHOP_PRICE_PER_BED}⭐")
        return
    if not user["beds_data"][bed_idx]["crop"]:
        await call.answer("Грядка пуста, нельзя охранять")
        return

    user["stars"] -= CHOP_PRICE_PER_BED
    if "chop_guarded" not in user:
        user["chop_guarded"] = []
    if bed_idx not in user["chop_guarded"]:
        user["chop_guarded"].append(bed_idx)

    await call.message.edit_text("✅ Грядка под охраной!", reply_markup=chairman_kb(call.from_user.id))


@router.callback_query(F.data == "chop_all")
async def chop_guard_all(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    total_cost = user["beds"] * CHOP_PRICE_PER_BED

    if user.get("stars", 0) < total_cost:
        await call.answer(f"Недостаточно звёзд! Нужно {total_cost}⭐")
        return

    user["stars"] -= total_cost
    user["chop_guarded"] = list(range(user["beds"]))
    await call.message.edit_text("✅ Все грядки под охраной!", reply_markup=chairman_kb(call.from_user.id))


@router.callback_query(F.data == "noop")
async def noop(call: types.CallbackQuery):
    await call.answer("Ничего не происходит")