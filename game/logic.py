# game/logic.py
import time
from typing import Dict, Tuple, Optional

# Базовые настройки
CLICK_BASE_COST = 50           # базовая цена прокачки клика (уровень 1)
PASSIVE_BASE_COST = 100        # базовая цена прокачки пассива (уровень 1)
GOLD_BASE_COST = 500           # базовая цена золотого банана
CLICK_COST_MULTIPLIER = 1.6    # рост цены за уровень
PASSIVE_COST_MULTIPLIER = 1.7
GOLD_COST_MULTIPLIER = 1.8
GOLD_DURATION = 300            # длительность "золотого" эффекта в секундах (5 минут)
OFFLINE_CAP_SECONDS = 60 * 60 * 24  # максимум начислений оффлайн (суточный лимит)

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
    elif upgrade_type == "gold":
        return gold_upgrade_cost(current_level)
    else:
        return 0

def click_upgrade_cost(level: int) -> int:
    """
    Цена следующего уровня клика.
    """
    return max(1, int(CLICK_BASE_COST * (CLICK_COST_MULTIPLIER ** level)))

def passive_upgrade_cost(level: int) -> int:
    """
    Цена следующего уровня пассива.
    """
    return max(1, int(PASSIVE_BASE_COST * (PASSIVE_COST_MULTIPLIER ** level)))

def gold_upgrade_cost(level: int) -> int:
    """
    Цена следующего золотого банана.
    """
    return max(1, int(GOLD_BASE_COST * (GOLD_COST_MULTIPLIER ** level)))

def calculate_per_click(upgrades: Dict) -> int:
    """
    Рассчитывает сколько бананов даёт один клик.
    """
    base_click = 1
    click_level = upgrades.get("click", 0)
    return base_click + click_level

def calculate_per_second(upgrades: Dict) -> int:
    """
    Рассчитывает пассивный доход в секунду.
    """
    collector_level = upgrades.get("collector", 0)
    return collector_level

# ---------- Оффлайн начисления ----------

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    """
    Вычисляет сколько бананов добавить пользователю за оффлайн время.
    """
    last = user.get("last_update", 0) or 0
    now = current_time()
    elapsed = now - last
    if elapsed <= 0:
        return 0, now

    # Ограничим начисления оффлайн
    if elapsed > OFFLINE_CAP_SECONDS:
        elapsed = OFFLINE_CAP_SECONDS

    # Получаем per_second
    per_second = user.get("per_second", None)
    if per_second is None or per_second == 0:
        per_second = calculate_per_second(user.get("upgrades", {}))

    # Учитываем event_multiplier если есть
    multiplier = user.get("event_multiplier", 1.0) or 1.0

    added = int(per_second * elapsed * multiplier)
    new_last = now
    return added, new_last

# ---------- Проверки и покупки ----------

def can_afford(user: Dict, price: int) -> bool:
    return (user.get("bananas", 0) or 0) >= price

def buy_click_upgrade(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Пытается купить апгрейд клика.
    """
    upgrades = user.get("upgrades", {}) or {}
    click_level = upgrades.get("click", 0)
    price = click_upgrade_cost(click_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    # Списываем и повышаем уровень
    bananas -= price
    upgrades["click"] = click_level + 1

    db.update_user(user_id, bananas=bananas, upgrades=upgrades)
    return True, f"✅ Улучшение клика куплено! Уровень: {upgrades['click']}. Списано: {price} 🍌."

def buy_passive_upgrade(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Пытается купить пассив (collector).
    """
    upgrades = user.get("upgrades", {}) or {}
    collector_level = upgrades.get("collector", 0)
    price = passive_upgrade_cost(collector_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    bananas -= price
    upgrades["collector"] = collector_level + 1
    # Рассчитаем новый per_second и сохраним его
    per_second = calculate_per_second(upgrades)
    db.update_user(user_id, bananas=bananas, upgrades=upgrades, per_second=per_second)
    return True, f"✅ Улучшение сборщика куплено! Уровень: {upgrades['collector']}. Списано: {price} 🍌."

def buy_gold_banana(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Пытается купить золотой банан.
    """
    upgrades = user.get("upgrades", {}) or {}
    gold_level = upgrades.get("gold", 0)
    price = gold_upgrade_cost(gold_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"❌ Недостаточно бананов! Нужно {price} 🍌, у вас {bananas} 🍌."

    bananas -= price
    upgrades["gold"] = gold_level + 1
    
    # Добавляем в инвентарь
    inventory = user.get("inventory", {}) or {}
    inventory["gold_banana"] = inventory.get("gold_banana", 0) + 1
    
    db.update_user(user_id, bananas=bananas, upgrades=upgrades, inventory=inventory)
    return True, f"✅ Золотой банан куплен! Добавлен в инвентарь. Всего куплено: {upgrades['gold']}. Списано: {price} 🍌."

# ---------- Перерождение (rebirth) ----------

def get_rebirth_requirement(rebirth_count: int) -> int:
    """
    Требование для следующего перерождения.
    """
    base = 1000
    return int(base * (2 ** rebirth_count))

def get_rebirth_reward(rebirth_count: int) -> Dict:
    """
    Возвращает награду за перерождение.
    """
    return {
        "click_bonus": 1,
        "gold_bananas": max(1, rebirth_count // 5 + 1)
    }

def perform_rebirth(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Делает перерождение.
    """
    bananas = user.get("bananas", 0) or 0
    rebirths = user.get("rebirths", 0) or 0
    req = get_rebirth_requirement(rebirths)

    if bananas < req:
        return False, f"❌ Для перерождения нужно {req} 🍌, у вас {bananas} 🍌."

    new_rebirths = rebirths + 1
    reward = get_rebirth_reward(new_rebirths)

    # Бонусы за перерождение
    upgrades = user.get("upgrades", {}) or {}
    upgrades["click"] = upgrades.get("click", 0) + reward["click_bonus"]

    # Добавляем золотые бананы в инвентарь
    inventory = user.get("inventory", {}) or {}
    inventory["gold_banana"] = inventory.get("gold_banana", 0) + reward["gold_bananas"]

    # Сбрасываем прогресс
    new_bananas = 0
    new_per_second = calculate_per_second(upgrades)

    # Обновляем пользователя
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
    """
    Возвращает эффективный per_click с учётом апгрейдов и ивентов.
    """
    upgrades = user.get("upgrades", {}) or {}
    base = calculate_per_click(upgrades)
    multiplier = 1.0
    
    # Умножаем на золотой банан если активен
    if has_active_gold(user):
        multiplier *= 2.0
    
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

def has_active_gold(user: Dict) -> bool:
    """Проверяет, активен ли золотой банан."""
    expires = user.get("gold_expires", 0)
    return expires > current_time()

def has_active_event(user: Dict) -> bool:
    """Проверяет, активен ли ивент."""
    expires = user.get("event_expires", 0)
    return expires > current_time()

def parse_event_duration(duration_str: str) -> int:
    """
    Парсит строку длительности в формате 'часы:минуты' в секунды.
    """
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
