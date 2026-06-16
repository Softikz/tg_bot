import os
import json
from datetime import datetime, timedelta, time

BOT_TOKEN = "8778080709:AAGbw1tt8Lpr4Qwjqu4tBQ4OXRxHxdVMz2o"
ADMIN_ID = 5748972158

CHOP_PRICE_PER_BED = 2
VIP_PRICE = 99
VIP_DURATION = timedelta(weeks=1)
PERMISSION_TIME = timedelta(hours=8)

LEVEL_EXP = [100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000]

TITLES = [
    "Новичок", "Любитель", "Фермер", "Агроном", "Мастер",
    "Профессионал", "Эксперт", "Магистр", "Великий фермер", "Легенда",
]

DEFAULT_SEEDS = {"🥕": 10}

CROP_GROW_TIMES = {
    "🥕": 1, "🧅": 1, "🥔": 10, "🥦": 8,
    "🌾": 60, "🌽": 50, "🍓": 300, "🍇": 240,
    "🍚": 720, "🍠": 600, "🎃": 1440, "🍆": 1200,
    "🍋": 240, "🍒": 240, "🌼": 240,
}

CROP_YIELDS = {
    "🥕": 4, "🧅": 8, "🥔": 6, "🥦": 8,
    "🌾": 10, "🌽": 12, "🍓": 12, "🍇": 14,
    "🍚": 14, "🍠": 16, "🎃": 16, "🍆": 18,
    "🍋": 12, "🍒": 16,
}

CROP_EXP = {
    "🥕": 1, "🧅": 5, "🥔": 15, "🥦": 15,
    "🌾": 30, "🌽": 30, "🍓": 100, "🍇": 100,
    "🍚": 150, "🍠": 150, "🎃": 300, "🍆": 300,
    "🍋": 200, "🍒": 50,
}

CROP_SELL_PRICE = {
    "🥕": 1, "🧅": 1, "🥔": 5, "🥦": 5,
    "🌾": 20, "🌽": 20, "🍓": 100, "🍇": 100,
    "🍚": 150, "🍠": 150, "🎃": 300, "🍆": 300,
    "🍋": 100, "🍒": 100,
}

users = {}

DATA_FILE = "users.json"

def get_user(user_id: int):
    if user_id not in users:
        users[user_id] = {
            "name": "",
            "title": TITLES[0],
            "level": 1,
            "exp": 0,
            "money": 0,
            "stars": 10,
            "beds": 2,
            "permissions": 0,
            "luck_tickets": 0,
            "seeds": DEFAULT_SEEDS.copy(),
            "harvest": {},
            "vip_until": None,
            "beds_data": [
                {"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None},
                {"crop": None, "planted_at": None, "grow_time": 0, "last_planted": None}
            ],
            "chop_guarded": [],
            "permit_pending": None,
            "permit_ready": False,
            "tutorial_complete": False,
            "play_time": "0ч",
            "registered_at": datetime.now().isoformat(),
        }
        # Нормализуем структуру нового пользователя
        normalize_user(users[user_id])
    else:
        # Нормализуем структуру при каждом доступе на случай, если данные были загружены старой версии
        normalize_user(users[user_id])
    return users[user_id]


def normalize_user(user: dict):
    """Нормализует ключи семян и поля beds_data для одного пользователя."""
    # Нормализуем seeds: приводим ключи к emoji, суммируем дубликаты
    seeds = user.get("seeds")
    if isinstance(seeds, dict):
        new_seeds = {}
        for k, v in seeds.items():
            new_key = None
            if k in CROP_GROW_TIMES:
                new_key = k
            else:
                # пробуем извлечь первую часть до пробела
                if isinstance(k, str) and ' ' in k:
                    first = k.split(' ')[0]
                    if first in CROP_GROW_TIMES:
                        new_key = first
                # иначе ищем вхождение ключа
                if not new_key and isinstance(k, str):
                    for key in CROP_GROW_TIMES.keys():
                        if key in k:
                            new_key = key
                            break
            if not new_key:
                new_key = k
            new_seeds[new_key] = new_seeds.get(new_key, 0) + (v or 0)
        user["seeds"] = new_seeds

    # Нормализуем beds_data: crop -> emoji и выставляем grow_time
    beds = user.get("beds_data")
    if isinstance(beds, list):
        for bed in beds:
            crop = bed.get("crop")
            if crop and isinstance(crop, str):
                if crop not in CROP_GROW_TIMES:
                    new_crop = None
                    if ' ' in crop:
                        first = crop.split(' ')[0]
                        if first in CROP_GROW_TIMES:
                            new_crop = first
                    if not new_crop:
                        for key in CROP_GROW_TIMES.keys():
                            if key in crop:
                                new_crop = key
                                break
                    if new_crop:
                        bed['crop'] = new_crop
                        bed['grow_time'] = CROP_GROW_TIMES.get(new_crop, bed.get('grow_time', 1))
                else:
                    bed['grow_time'] = CROP_GROW_TIMES.get(crop, bed.get('grow_time', 1))

def save_data():
    try:
        data_to_save = {}
        for uid, data in users.items():
            data_copy = {}
            for key, value in data.items():
                if key in ["vip_until", "permit_pending"] and value is not None:
                    if isinstance(value, datetime):
                        data_copy[key] = value.isoformat()
                    else:
                        data_copy[key] = value
                elif key == "beds_data":
                    beds_copy = []
                    for bed in value:
                        bed_copy = bed.copy()
                        for bk in ["planted_at", "last_planted"]:
                            if bed_copy.get(bk) and isinstance(bed_copy[bk], datetime):
                                bed_copy[bk] = bed_copy[bk].isoformat()
                        beds_copy.append(bed_copy)
                    data_copy[key] = beds_copy
                elif key == "registered_at" and isinstance(value, datetime):
                    data_copy[key] = value.isoformat()
                elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
                    data_copy[key] = value
                else:
                    data_copy[key] = str(value)
            data_to_save[str(uid)] = data_copy

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"💾 Сохранено пользователей: {len(users)}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")

def load_data():
    global users
    if not os.path.exists(DATA_FILE):
        print("📄 Файл users.json не найден. Начинаем с чистого листа.")
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        count = 0
        for uid, data in loaded.items():
            for key in ["vip_until", "permit_pending"]:
                if data.get(key) and isinstance(data[key], str):
                    try:
                        data[key] = datetime.fromisoformat(data[key])
                    except:
                        data[key] = None
            if "beds_data" in data:
                for bed in data["beds_data"]:
                    for bk in ["planted_at", "last_planted"]:
                        if bed.get(bk) and isinstance(bed[bk], str):
                            try:
                                bed[bk] = datetime.fromisoformat(bed[bk])
                            except:
                                bed[bk] = None
            if data.get("registered_at") and isinstance(data["registered_at"], str):
                try:
                    data["registered_at"] = datetime.fromisoformat(data["registered_at"])
                except:
                    data["registered_at"] = datetime.now()
            # Нормализуем пользователя после загрузки
            try:
                normalize_user(data)
            except Exception:
                pass
            users[int(uid)] = data
            count += 1
        print(f"📥 Загружено пользователей: {count}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

load_data()
bot = None  # Будет установлен из main.py