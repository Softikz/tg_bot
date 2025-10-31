# game/logic.py
import time
from typing import Dict, Tuple

# Базовые стоимости улучшений
CLICK_BASE_COST = 50

# Длительность золотого банана в секундах
GOLD_DURATION = 300  # 5 минут

# Требования для перерождения
def get_rebirth_requirement(rebirth_count: int) -> int:
    """Получить требование бананов для перерождения"""
    if rebirth_count == 0:
        return 1000
    elif rebirth_count == 1:
        return 2000
    elif rebirth_count == 2:
        return 4000
    else:
        # Экспоненциальный рост: 1000, 2000, 4000, 8000, 16000...
        return 1000 * (2 ** rebirth_count)

def get_rebirth_reward(rebirth_count: int) -> str:
    """Получить награду за перерождение"""
    rewards = [
        "🎁 +1 Золотой Банан в инвентарь",
        "🎁 +2 Золотых Банана в инвентарь", 
        "🎁 +3 Золотых Банана + 🚀 Умножение кликов x1.5",
        "🎁 +5 Золотых Бананов + 🚀 Умножение кликов x2",
        "🎁 +8 Золотых Бананов + 🚀 Умножение кликов x3"
    ]
    return rewards[min(rebirth_count, len(rewards)-1)]

def cost_for_upgrade(kind: str, level: int) -> int:
    if kind == "click":
        if level == 0:
            return CLICK_BASE_COST
        else:
            prev_cost = cost_for_upgrade("click", level-1)
            increase = 150 + 50 * (level - 1)
            return prev_cost + increase
    elif kind == "collector":
        return 100 * (level + 1) * 2
    elif kind == "gold":
        return 1000 * (level + 1) * 2
    else:
        return 100 * (level + 1) * 2

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    now = time.time()
    last = user.get("last_update", now)
    elapsed = int(now - last)
    if elapsed <= 0:
        return 0, now
    
    per_second = user.get("per_second", 0)
    added = per_second * elapsed
    return added, now

def has_active_gold(user: Dict) -> bool:
    return user.get("gold_expires", 0) > time.time()

def has_active_event(user: Dict) -> bool:
    return user.get("event_expires", 0) > time.time()

def get_event_multiplier(user: Dict) -> float:
    if has_active_event(user):
        return user.get("event_multiplier", 1.0)
    return 1.0

def gold_multiplier(user: Dict) -> int:
    return 2 if has_active_gold(user) else 1

def effective_per_click(user: Dict) -> int:
    base_click = user.get("per_click", 1)
    event_multiplier = get_event_multiplier(user)
    rebirth_multiplier = 1.0 + (user.get("rebirths", 0) * 0.5)  # +0.5 за каждое перерождение
    return int(base_click * gold_multiplier(user) * event_multiplier * rebirth_multiplier)

def calculate_per_click(upgrades: Dict) -> int:
    click_level = upgrades.get("click", 0)
    return 1 + click_level

def calculate_per_second(upgrades: Dict) -> int:
    collector_level = upgrades.get("collector", 0)
    return collector_level

def parse_event_duration(duration_str: str) -> int:
    try:
        if ':' in duration_str:
            hours, minutes = map(int, duration_str.split(':'))
            return hours * 3600 + minutes * 60
        else:
            return int(duration_str) * 3600
    except (ValueError, AttributeError):
        raise ValueError("Неверный формат длительности. Используйте 'часы:минуты'")
