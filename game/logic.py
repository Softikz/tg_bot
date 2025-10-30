# game/logic.py
import time
from typing import Dict, Tuple

# Базовые стоимости улучшений
COSTS = {
    "click": 50,        # базовая стоимость улучшения клика
    "collector": 100,   # базовая стоимость сборщика
    "gold": 1000        # базовая стоимость золотого банана
}

# Длительность золотого банана в секундах
GOLD_DURATION = 300  # 5 минут

def cost_for_upgrade(kind: str, level: int) -> int:
    """Рассчитать стоимость улучшения"""
    base = COSTS.get(kind, 100)
    # Увеличиваем стоимость с каждым уровнем
    return base * (level + 1) * 2  # Умножаем на 2 для прогрессии

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    """Применить оффлайн заработок"""
    now = time.time()
    last = user.get("last_update", now)
    elapsed = int(now - last)
    if elapsed <= 0:
        return 0, now
    
    per_second = user.get("per_second", 0)
    added = per_second * elapsed
    return added, now

def has_active_gold(user: Dict) -> bool:
    """Проверить активен ли золотой банан"""
    return user.get("gold_expires", 0) > time.time()

def gold_multiplier(user: Dict) -> int:
    """Множитель золотого банана"""
    return 2 if has_active_gold(user) else 1

def effective_per_click(user: Dict) -> int:
    """Эффективные клики с учетом золотого банана"""
    base_click = user.get("per_click", 1)
    return int(base_click * gold_multiplier(user))

def calculate_per_click(upgrades: Dict) -> int:
    """Рассчитать силу клика на основе улучшений"""
    click_level = upgrades.get("click", 0)
    # Каждое улучшение клика дает +1 к базовому урону
    return 1 + click_level

def calculate_per_second(upgrades: Dict) -> int:
    """Рассчитать пассивный доход на основе улучшений"""
    collector_level = upgrades.get("collector", 0)
    # Каждое улучшение сборщика дает +1 банан в секунду
    return collector_level
