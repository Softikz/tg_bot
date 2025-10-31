# game/logic.py
import time
from typing import Dict, Tuple

# Базовые стоимости улучшений
CLICK_BASE_COST = 50  # Начальная цена улучшения клика

# Длительность золотого банана в секундах
GOLD_DURATION = 300  # 5 минут

def cost_for_upgrade(kind: str, level: int) -> int:
    """Рассчитать стоимость улучшения с новой прогрессией"""
    if kind == "click":
        # Новая прогрессия: 50, 200, 300, 450, 650, 900...
        if level == 0:
            return CLICK_BASE_COST  # 50
        elif level == 1:
            return 200  # 50 + 150
        elif level == 2:
            return 300  # 200 + 100
        else:
            # Для уровней >=3: 450, 650, 900...
            # Формула: предыдущая_цена + 150 + 50*(level-2)
            prev_cost = cost_for_upgrade("click", level-1)
            return prev_cost + 150 + 50 * (level - 2)
    elif kind == "collector":
        return 100 * (level + 1) * 2
    elif kind == "gold":
        return 1000 * (level + 1) * 2
    else:
        return 100 * (level + 1) * 2

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

def has_active_event(user: Dict) -> bool:
    """Проверить активен ли ивент"""
    return user.get("event_expires", 0) > time.time()

def get_event_multiplier(user: Dict) -> float:
    """Получить множитель активного ивента"""
    if has_active_event(user):
        return user.get("event_multiplier", 1.0)
    return 1.0

def gold_multiplier(user: Dict) -> int:
    """Множитель золотого банана"""
    return 2 if has_active_gold(user) else 1

def effective_per_click(user: Dict) -> int:
    """Эффективные клики с учетом золотого банана и ивентов"""
    base_click = user.get("per_click", 1)
    event_multiplier = get_event_multiplier(user)
    return int(base_click * gold_multiplier(user) * event_multiplier)

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

def parse_event_duration(duration_str: str) -> int:
    """Парсинг длительности ивента из формата 'часы:минуты' в секунды"""
    try:
        if ':' in duration_str:
            hours, minutes = map(int, duration_str.split(':'))
            return hours * 3600 + minutes * 60
        else:
            return int(duration_str) * 3600  # если только число - считаем как часы
    except (ValueError, AttributeError):
        raise ValueError("Неверный формат длительности. Используйте 'часы:минуты' (например: '1:30' или '0:45')")
