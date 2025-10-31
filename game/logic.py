# game/logic.py
import time
from typing import Dict, Tuple
from storage.db import DB

COSTS = {
    "click": 50,
    "collector": 100,
    "gold": 1000
}

GOLD_DURATION = 300  # 5 минут

def click_upgrade_cost(level: int) -> int:
    if level == 0:
        return 50
    price = 50
    increment = 150
    for i in range(level):
        price += increment
        increment += 50
    return price

def cost_for_upgrade(kind: str, level: int) -> int:
    if kind == "click":
        return click_upgrade_cost(level)
    base = COSTS.get(kind, 100)
    return base * (level + 1)

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

def effective_per_click(user: Dict, db: DB) -> int:
    base_click = user.get("per_click", 1)
    multiplier = gold_multiplier(user)
    event = db.get_active_event()
    if event and event["type"].startswith("clickx"):
        multiplier *= event["multiplier"]
    return int(base_click * multiplier)

def calculate_per_click(upgrades: Dict) -> int:
    return 1 + upgrades.get("click", 0)

def calculate_per_second(upgrades: Dict) -> int:
    return upgrades.get("collector", 0)
