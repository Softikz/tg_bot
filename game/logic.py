# game/logic.py
import time
from typing import Dict, Tuple

# --- Базовые стоимости апгрейдов ---
COSTS = {
    "click": 50,        # цена за +1 к клику
    "collector": 100,   # цена за +1 к пассиву
    "gold": 1000        # золотой банан
}

# --- Длительность эффекта золотого банана (в секундах) ---
GOLD_DURATION = 60


def cost_for_upgrade(kind: str, level: int) -> int:
    """
    Рассчитывает цену апгрейда.
    Формула: cost = base * (level + 1)
    level — текущий уровень (0, если апгрейд не куплен)
    """
    base = COSTS[kind]
    return base * (level + 1)


def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    """
    Вычисляет, сколько бананов накопилось оффлайн (пока бот был неактивен).
    Возвращает кортеж: (добавленные_бананы, новое_время)
    """
    now = time.time()
    last = user.get("last_update", now)
    elapsed = int(now - last)

    # Если пользователь заходил недавно — ничего не добавляем
    if elapsed <= 0:
        return 0, now

    per_second = user.get("per_second", 0)
    added = per_second * elapsed
    return added, now


def has_active_gold(user: Dict) -> bool:
    """
    Проверяет, активен ли эффект золотого банана.
    """
    return user.get("gold_expires", 0) > time.time()


def gold_multiplier(user: Dict) -> int:
    """
    Умножает доход, если золотой банан активен.
    """
    return 2 if has_active_gold(user) else 1


def effective_per_click(user: Dict) -> int:
    """
    Возвращает эффективное значение клика с учётом золотого банана.
    """
    return int(user.get("per_click", 1) * gold_multiplier(user))
