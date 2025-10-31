# handlers/commands.py (исправленная функция handle_click)
@router.callback_query(F.data == "click")
async def handle_click(callback: CallbackQuery):
    await callback.answer()
    
    # Получаем актуальные данные пользователя
    user = db.get_user(callback.from_user.id)
    if not user:
        # Если пользователя нет, создаем
        db.create_user_if_not_exists(callback.from_user.id, callback.from_user.username or "unknown")
        user = db.get_user(callback.from_user.id)
    
    # Применяем оффлайн заработок
    added, new_last = apply_offline_gain(user)
    if added:
        user["bananas"] += added
        user["last_update"] = new_last
    
    # Рассчитываем клик
    per_click = effective_per_click(user)
    
    # Обновляем баланс
    new_bananas = user['bananas'] + per_click
    db.update_user(
        callback.from_user.id, 
        bananas=new_bananas, 
        last_update=time.time()
    )
    
    # Получаем обновленные данные для отображения
    updated_user = db.get_user(callback.from_user.id)
    
    # Формируем текст
    text = (
        f"🍌 Клик! +{per_click}\n\n"
        f"Всего: {int(updated_user['bananas'])} 🍌\n"
        f"За клик: {effective_per_click(updated_user)}\n"
        f"Пассив: {updated_user['per_second']}/сек\n"
    )
    
    # Добавляем информацию об активных бустах
    boosts = []
    if has_active_gold(updated_user):
        remaining = int(updated_user.get("gold_expires", 0) - time.time())
        boosts.append(f"✨ Золотой банан (2×)")
    
    if has_active_event(updated_user):
        remaining = int(updated_user.get("event_expires", 0) - time.time())
        multiplier = updated_user.get("event_multiplier", 1.0)
        event_type = updated_user.get("event_type", "")
        boosts.append(f"🎯 {event_type} ({multiplier}×)")
    
    if boosts:
        text += "⚡ " + " + ".join(boosts) + "\n"
    
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())
