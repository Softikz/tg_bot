import random
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, users, CROP_YIELDS, CHOP_PRICE_PER_BED

router = Router()


@router.callback_query(F.data == "friends")
async def friends_main(call: types.CallbackQuery):
    await call.message.edit_text(
        "👥 Друзья и соседи\n\nПосещайте фермы других игроков, помогайте им и заводите новых друзей!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Рейтинги", callback_data="ratings")],
            [InlineKeyboardButton(text="🔎 Найти соседей", callback_data="find_neighbors")],
            [InlineKeyboardButton(text="🎣 Озеро", callback_data="fishing_enter")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")],
        ])
    )


@router.callback_query(F.data == "ratings")
async def ratings(call: types.CallbackQuery):
    sorted_users = sorted(
        [(uid, data) for uid, data in users.items() if data.get("name")],
        key=lambda x: (x[1].get("level", 1), x[1].get("exp", 0)),
        reverse=True
    )[:20]

    text = (
        "🏆 Рейтинг игроков\n\n"
        "Здесь вы можете увидеть топ-20 игроков по различным показателям.\n\n"
    )

    if not sorted_users:
        text += "Пока нет игроков в рейтинге.\n"
    else:
        text += "Топ:\n"
        for i, (uid, data) in enumerate(sorted_users, 1):
            # Расчёт времени в грядках
            registered = data.get("registered_at")
            if isinstance(registered, str):
                try:
                    registered = datetime.fromisoformat(registered)
                except:
                    registered = datetime.now()
            if isinstance(registered, datetime):
                delta = datetime.now() - registered
                days = delta.days
                hours = delta.seconds // 3600
                if days > 0:
                    play_time = f"{days}д {hours}ч"
                else:
                    play_time = f"{hours}ч"
            else:
                play_time = "0ч"

            text += f"{i}. {data['name']}\n"
            text += f"⏰ Времени в грядках: {play_time}\n"
            text += f"💰 Баланс: {data.get('money', 0)}\n\n"

    text += "\nНаграды выдаются еженедельно в 20:00 по Москве в воскресенье"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к друзьям", callback_data="friends")]
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "find_neighbors")
async def find_neighbors(call: types.CallbackQuery):
    others = [uid for uid in users if uid != call.from_user.id and users[uid].get("name")]
    random.shuffle(others)
    neighbors = others[:10]

    if not neighbors:
        await call.message.edit_text(
            "👥 Найдено 0 соседей.\n\nПока никто не зарегистрировался в боте.\nПригласите друзей!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Найти новых соседей", callback_data="find_neighbors")],
                [InlineKeyboardButton(text="⬅️ Назад к друзьям", callback_data="friends")]
            ])
        )
        return

    text = f"👥 Найдено {len(neighbors)} соседей.\n\nВыберите соседа, чтобы посетить его ферму:\n"
    buttons = []
    for uid in neighbors:
        name = users[uid]["name"]
        level = users[uid].get("level", 1)
        buttons.append([InlineKeyboardButton(text=f"👤 {name} (ур.{level})", callback_data=f"visit_{uid}")])

    buttons.append([InlineKeyboardButton(text="🔄 Найти новых соседей", callback_data="find_neighbors")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к друзьям", callback_data="friends")])

    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("visit_"))
async def visit_farm(call: types.CallbackQuery):
    visitor_id = call.from_user.id
    owner_id = int(call.data.replace("visit_", ""))

    if owner_id not in users:
        await call.answer("Игрок не найден")
        return

    owner = users[owner_id]
    visitor = get_user(visitor_id)
    now = datetime.now()

    buttons = []
    for i in range(owner["beds"]):
        bed = owner["beds_data"][i]
        if bed["crop"] is None:
            if bed.get("last_planted") and isinstance(bed["last_planted"], datetime):
                if (now - bed["last_planted"]).total_seconds() > 12 * 3600:
                    text = f"Грядка {i + 1}: 🌿 Заросла - 🧹 Расчистить"
                else:
                    text = f"Грядка {i + 1}: пусто🟫"
            elif bed.get("last_planted") and isinstance(bed["last_planted"], str):
                try:
                    last = datetime.fromisoformat(bed["last_planted"])
                    if (now - last).total_seconds() > 12 * 3600:
                        text = f"Грядка {i + 1}: 🌿 Заросла - 🧹 Расчистить"
                    else:
                        text = f"Грядка {i + 1}: пусто🟫"
                except:
                    text = f"Грядка {i + 1}: пусто🟫"
            else:
                text = f"Грядка {i + 1}: пусто🟫"
        elif bed["crop"] and bed["planted_at"]:
            planted = bed["planted_at"]
            if isinstance(planted, str):
                try:
                    planted = datetime.fromisoformat(planted)
                except:
                    planted = now
            elapsed = (now - planted).total_seconds() / 60
            if elapsed >= bed["grow_time"]:
                if i in owner.get("chop_guarded", []):
                    text = f"Грядка {i + 1}: {bed['crop']} созрела - 🛡️ Охрана"
                else:
                    text = f"Грядка {i + 1}: {bed['crop']} созрела - 🥷 Украсть"
            else:
                remain = bed["grow_time"] - elapsed
                hours = int(remain // 60)
                mins = int(remain % 60)
                text = f"Грядка {i + 1}: 🌳 зреет ({hours}ч {mins}м) - ⚡ Ускорить"
        else:
            text = f"Грядка {i + 1}: пусто🟫"

        buttons.append([InlineKeyboardButton(text=text, callback_data=f"neighbor_bed_{owner_id}_{i}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к соседям", callback_data="find_neighbors")])

    await call.message.edit_text(
        f"🌱 Ферма игрока {owner['name']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("neighbor_bed_"))
async def neighbor_bed_action(call: types.CallbackQuery):
    parts = call.data.split("_")
    owner_id = int(parts[2])
    bed_idx = int(parts[3])
    visitor_id = call.from_user.id

    if owner_id not in users:
        await call.answer("Игрок не найден")
        return

    owner = users[owner_id]
    visitor = get_user(visitor_id)
    bed = owner["beds_data"][bed_idx]
    now = datetime.now()

    # Расчистка
    if bed["crop"] is None:
        if visitor.get("permissions", 0) < 1:
            await call.answer("Нет разрешений! Получите у Председателя СНТ.")
            return
        visitor["permissions"] -= 1
        silos = random.randint(2, 5)
        visitor["harvest"]["🌿 Силос"] = visitor["harvest"].get("🌿 Силос", 0) + silos
        visitor["exp"] = visitor.get("exp", 0) + 15
        await call.message.edit_text(
            f"👨‍🌾 Вы расчистили заросшую грядку и получили 🌿 Силос x{silos}!\n\n"
            f"📜 Потрачено 1 разрешение. Осталось: {visitor['permissions']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к ферме", callback_data=f"visit_{owner_id}")]
            ])
        )
        return

    planted = bed["planted_at"]
    if isinstance(planted, str):
        try:
            planted = datetime.fromisoformat(planted)
        except:
            planted = now
    elapsed = (now - planted).total_seconds() / 60 if planted else 0

    # Кража
    if elapsed >= bed["grow_time"]:
        if visitor.get("permissions", 0) < 1:
            await call.answer("Нет разрешений на кражу!")
            return
        if bed_idx in owner.get("chop_guarded", []):
            await call.answer("🛡️ Грядка под охраной ЧОП! Нельзя украсть.")
            return

        crop = bed["crop"]
        amount = CROP_YIELDS.get(crop, 4) // 2
        visitor["harvest"][crop] = visitor["harvest"].get(crop, 0) + amount
        visitor["exp"] = visitor.get("exp", 0) + 50
        visitor["permissions"] -= 1
        owner["harvest"][crop] = owner["harvest"].get(crop, 0) + amount
        bed["crop"] = None
        bed["planted_at"] = None

        await call.message.edit_text(
            f"Вы успешно украли урожай!\n\n{crop}: +{amount} шт.\n🔹 Опыт: +50\n📜 Разрешений осталось: {visitor['permissions']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к ферме", callback_data=f"visit_{owner_id}")]
            ])
        )

        try:
            from config import bot
            await bot.send_message(
                owner_id,
                f"⚠️ Внимание! Игрок {visitor['name']} украл ваш урожай ({crop}) с грядки {bed_idx + 1}!\n\n"
                "Вы все еще можете собрать оставшуюся половину урожая на своей ферме.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="На свою ферму", callback_data="farm")],
                    [InlineKeyboardButton(text="Осмотреть ферму вора", callback_data=f"visit_{visitor_id}")]
                ])
            )
        except:
            pass
        return

    # Ускорение
    remain_hours = int((bed["grow_time"] - elapsed) // 60) + 1
    cost = remain_hours
    if visitor.get("stars", 0) < cost:
        await call.answer(f"Недостаточно звёзд! Нужно {cost}⭐, у вас {visitor.get('stars', 0)}⭐")
        return

    visitor["stars"] -= cost
    bed["planted_at"] = now - timedelta(minutes=bed["grow_time"])

    await call.message.edit_text(
        f"⭐️ Рост {bed['crop']} ускорен!\n\nСписано {cost}⭐.\nРастение теперь созрело.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к ферме", callback_data=f"visit_{owner_id}")]
        ])
    )

    try:
        from config import bot
        await bot.send_message(
            owner_id,
            f"⭐️ Хорошие новости! Игрок {visitor['name']} помог вам и ускорил рост вашего {bed['crop']} на грядке {bed_idx + 1}!\n\n"
            "Теперь вы можете собрать урожай.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="На свою ферму", callback_data="farm")],
                [InlineKeyboardButton(text="Осмотреть ферму вора", callback_data=f"visit_{visitor_id}")]
            ])
        )
    except:
        pass