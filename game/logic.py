# game/logic.py
import time
from typing import Dict, Tuple, Optional

# Базовые настройки
CLICK_BASE_COST = 50           # базовая цена прокачки клика (уровень 1)
PASSIVE_BASE_COST = 100        # базовая цена прокачки пассива (уровень 1)
CLICK_COST_MULTIPLIER = 1.6    # рост цены за уровень
PASSIVE_COST_MULTIPLIER = 1.7
GOLD_DURATION = 300            # длительность "золотого" эффекта в секундах (пример)
OFFLINE_CAP_SECONDS = 60 * 60 * 24  # максимум начислений оффлайн (суточный лимит)

# ---------- Вспомогательные функции ----------

def current_time() -> float:
    return time.time()

def format_cost(n: int) -> str:
    return f"{int(n)}"

# ---------- Стоимости и расчёты ----------

def click_upgrade_cost(level: int) -> int:
    """
    Цена следующего уровня клика (если level == 0 -> цена уровня 1).
    """
    # level - текущий уровень, цена для повышения = base * multiplier^(level)
    return max(1, int(CLICK_BASE_COST * (CLICK_COST_MULTIPLIER ** level)))

def passive_upgrade_cost(level: int) -> int:
    """
    Цена следующего уровня пассива (collector и т.п.)
    """
    return max(1, int(PASSIVE_BASE_COST * (PASSIVE_COST_MULTIPLIER ** level)))

def calculate_per_click(upgrades: Dict) -> int:
    """
    Рассчитывает сколько бананов даёт один клик, с учётом апгрейдов и возможных бонусов.
    upgrades: словарь уровней апгрейдов, например {"click": 3, ...}
    """
    base_click = 1
    click_level = upgrades.get("click", 0)
    # Простая формула: base + level * 1 (можно усложнить)
    return base_click + click_level

def calculate_per_second(upgrades: Dict) -> int:
    """
    Рассчитывает пассивный доход в секунду в зависимости от апгрейдов.
    """
    collector_level = upgrades.get("collector", 0)
    # Каждый уровень коллектора даёт 1 банан в секунду (пример)
    return collector_level

# ---------- Оффлайн начисления ----------

def apply_offline_gain(user: Dict) -> Tuple[int, float]:
    """
    Вызывается в фоне: вычисляет сколько бананов добавить пользователю,
    исходя из last_update и per_second (в user['per_second'] или на основании upgrades).
    Возвращает (added_amount, new_last_update_timestamp).
    Если ничего не добавлено — added_amount == 0.
    """
    last = user.get("last_update", 0) or 0
    now = current_time()
    elapsed = now - last
    if elapsed <= 0:
        return 0, now

    # Ограничим начисления оффлайн
    if elapsed > OFFLINE_CAP_SECONDS:
        elapsed = OFFLINE_CAP_SECONDS

    # Получаем per_second: сначала поле, иначе считаем по апгрейдам
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
    Пытается купить апгрейд клика. Возвращает (success, message).
    Изменяет и сохраняет данные через db.update_user.
    """
    upgrades = user.get("upgrades", {}) or {}
    click_level = upgrades.get("click", 0)
    price = click_upgrade_cost(click_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"У вас недостаточно бананов. Нужно {price}, у вас {bananas}."

    # Списываем и повышаем уровень
    bananas -= price
    upgrades["click"] = click_level + 1

    db.update_user(user_id, bananas=bananas, upgrades=upgrades)
    return True, f"Покупка успешна! Уровень клика теперь {upgrades['click']}. Списано {price} бананов."

def buy_passive_upgrade(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Пытается купить пассив (collector). Возвращает (success, message).
    """
    upgrades = user.get("upgrades", {}) or {}
    collector_level = upgrades.get("collector", 0)
    price = passive_upgrade_cost(collector_level)
    bananas = user.get("bananas", 0) or 0

    if bananas < price:
        return False, f"У вас недостаточно бананов. Нужно {price}, у вас {bananas}."

    bananas -= price
    upgrades["collector"] = collector_level + 1
    # Рассчитаем новый per_second и сохраним его
    per_second = calculate_per_second(upgrades)
    db.update_user(user_id, bananas=bananas, upgrades=upgrades, per_second=per_second)
    return True, f"Покупка успешна! Уровень пассива (collector) теперь {upgrades['collector']}. Списано {price} бананов."

# ---------- Перерождение (rebirth) ----------

def get_rebirth_requirement(rebirth_count: int) -> int:
    """
    Требование для следующего перерождения.
    Можно сделать экспоненциальный рост. Пример:
    """
    base = 1000
    return int(base * (2 ** rebirth_count))

def perform_rebirth(db, user_id: int, user: Dict) -> Tuple[bool, str]:
    """
    Делает перерождение: если пользователь достигает требуемого числа бананов,
    скидывает прогресс (частично) и добавляет бонусы (например, увеличивает rebirths).
    Возвращает (success, message).
    """
    bananas = user.get("bananas", 0) or 0
    rebirths = user.get("rebirths", 0) or 0
    req = get_rebirth_requirement(rebirths)

    if bananas < req:
        return False, f"Для перерождения нужно {req} бананов, у вас {bananas}."

    # Настройка того, что происходит при перерождении:
    # - увеличим счётчик rebirths
    # - дадим небольшой бонус: например, повысим per_click на 1 или дадим "rebirth_points" в inventory
    # - сбросим бананы и апгрейды (или частично)
    new_rebirths = rebirths + 1

    # Бонус — прибавим 1 уровень к клику (как простая награда), но не ниже 0
    upgrades = user.get("upgrades", {}) or {}
    upgrades["click"] = upgrades.get("click", 0) + 1

    # Сбросим основные ресурсы, но сохраним некоторые вещи:
    new_bananas = 0
    new_per_second = calculate_per_second(upgrades)

    # Обновляем пользователя
    db.update_user(user_id,
                   bananas=new_bananas,
                   rebirths=new_rebirths,
                   upgrades=upgrades,
                   per_second=new_per_second,
                   last_update=current_time())
    return True, f"🎉 Перерождение прошло успешно! Это ваше перерождение #{new_rebirths}. Вы получили +1 к уровню клика как бонус."

# ---------- Утилиты для просмотра состояния ----------

def effective_per_click(user: Dict) -> int:
    """
    Возвращает эффективный per_click с учётом апгрейдов и ивентов.
    """
    upgrades = user.get("upgrades", {}) or {}
    base = calculate_per_click(upgrades)
    multiplier = user.get("event_multiplier", 1.0) or 1.0
    return int(base * multiplier)

def effective_per_second(user: Dict) -> int:
    upgrades = user.get("upgrades", {}) or {}
    base = user.get("per_second", None)
    if base is None or base == 0:
        base = calculate_per_second(upgrades)
    multiplier = user.get("event_multiplier", 1.0) or 1.0
    return int(base * multiplier)
