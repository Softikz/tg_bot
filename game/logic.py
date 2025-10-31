# game/logic.py
import time
from typing import Dict, Tuple

COSTS = {
    "click": 50,
    "collector": 100,
    "gold": 1000
}

# длительность золотого банана в секундах
GOLD_DURATION = 300  # 5 минут

def cost_for_upgrade(kind: str, level: int) -> int:
    base = COSTS.get(kind, 100)
    return base * (level + 1) * 2

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

def gold_multiplier(user: Dict) -> int:
    return 2 if has_active_gold(user) else 1

def effective_per_click(user: Dict) -> int:
    base_click = user.get("per_click", 1)
    return int(base_click * gold_multiplier(user))

def calculate_per_click(upgrades: Dict) -> int:
    click_level = upgrades.get("click", 0)
    return 1 + click_level

def calculate_per_second(upgrades: Dict) -> int:
    collector_level = upgrades.get("collector", 0)
    return collector_level
