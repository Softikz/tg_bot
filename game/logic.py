# game/logic.py
import time
from typing import Dict, Tuple, Optional

# Базовые настройки
CLICK_BASE_COST = 50
PASSIVE_BASE_COST = 100

# Стоимости разных бананов
BANANA_TYPES = {
    "common_banana": {
        "name": "🍌 Обычный Банан",
        "base_cost": 100,
        "multiplier": 1.5,
        "duration": 300,
        "cost_multiplier": 1.5
    },
    "gold_banana": {
        "name": "✨ Золотой Банан", 
        "base_cost": 500,
        "multiplier": 2.0,
        "duration": 300,
        "cost_multiplier": 1.8
    },
    "crystal_banana": {
        "name": "💎 Кристальный Банан",
        "base_cost": 1500,
        "multiplier": 3.0,
        "duration": 300,
        "cost_multiplier": 2.0
    },
    "emerald_banana": {
        "name": "💚 Изумрудный Банан", 
        "base_cost": 3000,
        "multiplier": 4.0,
        "duration": 300,
        "cost_multiplier": 2.2
    },
    "ruby_banana": {
        "name": "❤️ Рубиновый Банан",
        "base_cost": 6000, 
        "multiplier": 5.0,
        "duration": 300,
        "cost_multiplier": 2.5
    },
    "diamond_banana": {
        "name": "🔷 Алмазный Банан",
        "base_cost": 13000,
        "multiplier": 7.0, 
        "duration": 300,
        "cost_multiplier": 3.0
    },
    "cosmic_banana": {
        "name": "🌌 Космический Банан",
        "base_cost": 50000,
        "multiplier": 10.0,
        "duration": 300,
        "cost_multiplier": 3.5
    },
    "mythical_banana": {
        "name": "🐉 Мифический Банан", 
        "base_cost": 100000,
        "multiplier": 15.0,
        "duration": 300,
        "cost_multiplier": 4.0
    },
    "godly_banana": {
        "name": "👑 Божественный Банан",
        "base_cost": 250000, 
        "multiplier": 30.0,
        "duration": 300,
        "cost_multiplier": 5.0
    }
}

CLICK_COST_MULTIPLIER = 1.6
PASSIVE_COST_MULTIPLIER = 1.7
OFFLINE_CAP_SECONDS = 60 * 60 * 3  # 3 часа вместо 24

# ---------- Вспомогательные функции ----------

def current_time() -> float:
    return time.time()

def format_cost(n: int) -> str:
    return f"{int(n)}"

# ---------- Стоимости и расчёты ----------

def cost_for_upgrade(upgrade_type: str, current_level: int) -> int:
    """
    Рассчитывает стоимость улучшения для указанного типа.
    """
    if upgrade_type == "click":
        return click_upgrade_cost(current_level)
    elif upgrade_type == "collector":
        return passive_upgrade_cost(current_level)
    elif upgrade_type in BANANA_TYPES:
        return banana_upgrade_cost(upgrade_type, current_level)
    else:
        return 0

def click_upgrade_cost(level: int) -> int:
    return max(1, int(CLICK_BASE_COST * (CLICK_COST_MULTIPLIER ** level)))

def passive_upgrade_cost(level: int) -> int:
    return max(1, int(PASSIVE_BASE_COST * (PASSIVE_COST_MULTIPLIER ** level)))

def banana_upgrade_cost(banana_type: str, level: int) -> int:
    """
    Цена следующего банана указанного типа.
    """
    banana_data = BANANA_TYPES.get(banana_type)
    if not banana_data:
        return 0
    return max(1, int(banana_data["base_cost"] * (banana_data["cost_multiplier"] ** level)))

def get_banana_data(banana_type: str) -> Dict:
    """Возвращает данные о банане по его типу."""
    return BANANA_TYPES.get(banana_type, {})

def get_all_banana_types() -> list:
    """Возвращает список всех типов бананов."""
    return list(BANANA_TYPES.keys())

def calculate_per_click(upgrades: Dict) -> int:
    base_click = 1
    click_level = upgrades.get("click", 0)
    return base_click + click_level

def calculate_per_second(upgrades: Dict) -> int:
    collector_level = upgrades.get("collector", 0)
    return collector_level

# ---------- Оффлайн начисления ----------

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    last = user.get("last_update", 0) or 0
    now = current_time()
    elapsed = now - last
    if elapsed <= 0:
        return 0, now

    if elapsed > OFFLINE_CAP_SECONDS:
        elapsed = OFFLINE_CAP_SECONDS

    per_second = user.get("per_second", None)
    if per_second is None or per_second == 0:
        per_second = calculate_per_second(user.get("upgrades", {}))

    multiplier = user.get("event_multiplier", 1.0) or 1.0

    added = int(per_second * elapsed * multiplier)
    new_last = now
    return added, new_last

# ---------- Проверки и покупки ----------

def can_afford(user: Dict, price: int) -> bool:
    return (user.get("bananas", 0) or 0) >= price

def buy_click_upgrade(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    upgrades = user.get("upgrades", {}) or {}
    click_level = upgrades.get("click", 0)
    price = click_upgrade_cost(click_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    bananas -= price
    upgrades["click"] = click_level + 1

    db.update_user(user_id, bananas=bananas, upgrades=upgrades)
    return True, f"✅ Улучшение клика куплено! Уровень: {upgrades['click']}. Списано: {price} 🍌."

def buy_passive_upgrade(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    upgrades = user.get("upgrades", {}) or {}
    collector_level = upgrades.get("collector", 0)
    price = passive_upgrade_cost(collector_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    bananas -= price
    upgrades["collector"] = collector_level + 1
    per_second = calculate_per_second(upgrades)
    db.update_user(user_id, bananas=bananas, upgrades=upgrades, per_second=per_second)
    return True, f"✅ Улучшение сборщика куплено! Уровень: {upgrades['collector']}. Списано: {price} 🍌."

def buy_banana(db, user_id: int, user: Dict, banana_type: str) -> Tuple[bool, str]:
    """
    Пытается купить банан указанного типа.
    """
    if banana_type not in BANANA_TYPES:
        return False, "❌ Неизвестный тип банана!"
    
    banana_data = BANANA_TYPES[banana_type]
    upgrades = user.get("upgrades", {}) or {}
    
    # Получаем уровень для этого типа банана
    banana_level_key = f"{banana_type}_level"
    banana_level = upgrades.get(banana_level_key, 0)
    
    price = banana_upgrade_cost(banana_type, banana_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    bananas -= price
    upgrades[banana_level_key] = banana_level + 1
    
    # Добавляем в инвентарь
    inventory = user.get("inventory", {}) or {}
    inventory[banana_type] = inventory.get(banana_type, 0) + 1
    
    db.update_user(user_id, bananas=bananas, upgrades=upgrades, inventory=inventory)
    return True, f"✅ {banana_data['name']} куплен! Добавлен в инвентарь. Всего куплено: {upgrades[banana_level_key]}. Списано: {price} 🍌."

# ---------- Использование бананов ----------

def use_banana(db, user_id: int, user: Dict, banana_type: str) -> Tuple[bool, str]:
    """
    Использует банан из инвентаря.
    """
    if banana_type not in BANANA_TYPES:
        return False, "❌ Неизвестный тип банана!"
    
    banana_data = BANANA_TYPES[banana_type]
    
    # Проверяем наличие в инвентаре
    inventory = user.get("inventory", {}) or {}
    if inventory.get(banana_type, 0) < 1:
        return False, f"❌ Нет {banana_data['name']} в инвентаре!"
    
    # Используем банан из инвентаря
    inventory[banana_type] -= 1
    if inventory[banana_type] <= 0:
        del inventory[banana_type]
    
    # Активируем банан - устанавливаем время окончания
    current_time_val = current_time()
    new_expires = current_time_val + banana_data["duration"]
    
    # Сохраняем изменения
    db.update_user(
        user_id, 
        inventory=inventory,
        gold_expires=new_expires,
        active_banana_type=banana_type,
        active_banana_multiplier=banana_data["multiplier"]
    )
    
    remaining = inventory.get(banana_type, 0)
    remaining_time = int(new_expires - current_time_val)
    
    return True, (
        f"✅ {banana_data['name']} активирован! "
        f"+{banana_data['duration']//60} минут буста {banana_data['multiplier']}×.\n"
        f"⏰ Осталось времени: {remaining_time//60:02d}:{remaining_time%60:02d}\n"
        f"📦 Осталось в инвентаре: {remaining}"
    )

# ---------- Перерождение (rebirth) ----------

def get_rebirth_requirement(rebirth_count: int) -> int:
    base = 1000
    return int(base * (2 ** rebirth_count))

def get_rebirth_reward(rebirth_count: int) -> Dict:
    return {
        "click_bonus": 1,
        "gold_bananas": max(1, rebirth_count // 5 + 1)
    }

def perform_rebirth(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    bananas = user.get("bananas", 0) or 0
    rebirths = user.get("rebirths", 0) or 0
    req = get_rebirth_requirement(rebirths)

    if bananas < req:
        return False, f"❌ Для перерождения нужно {req} 🍌, у вас {bananas} 🍌."

    new_rebirths = rebirths + 1
    reward = get_rebirth_reward(new_rebirths)

    upgrades = user.get("upgrades", {}) or {}
    upgrades["click"] = upgrades.get("click", 0) + reward["click_bonus"]

    inventory = user.get("inventory", {}) or {}
    inventory["gold_banana"] = inventory.get("gold_banana", 0) + reward["gold_bananas"]

    new_bananas = 0
    new_per_second = calculate_per_second(upgrades)

    db.update_user(user_id,
                   bananas=new_bananas,
                   rebirths=new_rebirths,
                   upgrades=upgrades,
                   per_second=new_per_second,
                   inventory=inventory,
                   last_update=current_time())
    
    reward_text = f"+{reward['click_bonus']} к уровню клика"
    if reward["gold_bananas"] > 0:
        reward_text += f", +{reward['gold_bananas']} золотых бананов"
    
    return True, f"🎉 Перерождение #{new_rebirths} успешно! Награды: {reward_text}."

# ---------- Утилиты для просмотра состояния ----------

def effective_per_click(user: Dict) -> int:
    upgrades = user.get("upgrades", {}) or {}
    base = calculate_per_click(upgrades)
    multiplier = 1.0
    
    # Умножаем на активный банан если есть
    if has_active_banana(user):
        multiplier *= user.get("active_banana_multiplier", 1.0)
    
    # Умножаем на ивент если активен
    if has_active_event(user):
        multiplier *= user.get("event_multiplier", 1.0)
    
    return int(base * multiplier)

def effective_per_second(user: Dict) -> int:
    upgrades = user.get("upgrades", {}) or {}
    base = user.get("per_second", None)
    if base is None or base == 0:
        base = calculate_per_second(upgrades)
    
    multiplier = 1.0
    if has_active_event(user):
        multiplier = user.get("event_multiplier", 1.0)
    
    return int(base * multiplier)

def has_active_banana(user: Dict) -> bool:
    """Проверяет, активен ли любой банан."""
    expires = user.get("gold_expires", 0)
    banana_type = user.get("active_banana_type", "")
    # Проверяем что время не истекло И тип банана существует
    return expires > current_time() and banana_type in BANANA_TYPES

def get_active_banana_type(user: Dict) -> str:
    """Возвращает тип активного банана."""
    banana_type = user.get("active_banana_type", "")
    # Возвращаем только если тип существует и активен
    if banana_type in BANANA_TYPES and has_active_banana(user):
        return banana_type
    return ""

def get_active_banana_multiplier(user: Dict) -> float:
    """Возвращает множитель активного банана."""
    if has_active_banana(user):
        return user.get("active_banana_multiplier", 1.0)
    return 1.0

def get_active_banana_info(user: Dict) -> Tuple[str, float, int]:
    """Возвращает информацию об активном банане: (тип, множитель, оставшееся время)."""
    if not has_active_banana(user):
        return "", 1.0, 0
    
    banana_type = user.get("active_banana_type", "")
    multiplier = user.get("active_banana_multiplier", 1.0)
    expires = user.get("gold_expires", 0)
    remaining = max(0, int(expires - current_time()))
    
    return banana_type, multiplier, remaining

def has_active_event(user: Dict) -> bool:
    expires = user.get("event_expires", 0)
    return expires > current_time()

def parse_event_duration(duration_str: str) -> int:
    try:
        parts = duration_str.split(':')
        if len(parts) != 2:
            raise ValueError("Неверный формат. Используйте 'часы:минуты'")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        
        if hours < 0 or minutes < 0 or minutes >= 60:
            raise ValueError("Часы должны быть >= 0, минуты от 0 до 59")
        
        return hours * 3600 + minutes * 60
    except ValueError as e:
        raise ValueError(f"Ошибка парсинга времени: {str(e)}")
