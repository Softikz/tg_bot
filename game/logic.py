# game/logic.py
import time
from typing import Dict, Tuple

COSTS = {
    "click": 50,
    "collector": 100,
    "gold": 1000
}

GOLD_DURATION = 60  # секунд


def cost_for_upgrade(kind: str, level: int) -> int:
    base = COSTS[kind]
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


def effective_per_click(user: Dict) -> int:
    return int(user.get("per_click", 1) * gold_multiplier(user))
