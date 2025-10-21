# game/logic.py
import time
from typing import Dict, Tuple

# Base costs
COSTS = {
    "click": 50,        # base for +1 per click
    "collector": 100,   # base for +1 per second
    "gold": 1000        # golden banana powerup
}

# Gold effect duration in seconds
GOLD_DURATION = 60

def cost_for_upgrade(kind: str, level: int) -> int:
    """
    cost = base * (level + 1)
    level is current level (0 if unbought); purchase will raise it by 1.
    """
    base = COSTS[kind]
    return base * (level + 1)

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    """
    Calculates passive gain since last_update and updates last_update.
    Returns (added_bananas, new_last_update)
    """
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
