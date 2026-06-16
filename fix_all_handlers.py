import os

# Список файлов, которые нужно исправить
files_to_fix = [
    "handlers_deliveries.py",
    "handlers_profile.py",
    "handlers_library.py",
    "handlers_museum.py",
    "handlers_friends.py",
    "handlers_janna.py",
    "handlers_mine.py",
    "handlers_fishing.py",
    "handlers_coop.py",
    "handlers_weekly.py",
    "handlers_festival.py",
    "handlers_shop.py",
    "handlers_flowerbed.py",
]

# Базовые импорты, которые нужны всем
base_imports = """from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_user, bot
import random
from datetime import datetime, timedelta

router = Router()

"""

for filename in files_to_fix:
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # Если в файле уже есть router, пропускаем
        if 'router = Router()' in content:
            print(f"✓ {filename} уже исправлен")
            continue

        # Убираем старые импорты aiogram, если они есть в начале
        lines = content.split('\n')
        new_lines = []
        skip_imports = False

        for line in lines:
            if line.startswith('from aiogram') or line.startswith('import aiogram'):
                continue
            if line.startswith('from config import') or line.startswith('from keyboards import'):
                continue
            new_lines.append(line)

        # Собираем новый файл
        new_content = base_imports + '\n'.join(new_lines)

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✓ {filename} исправлен")
    else:
        print(f"✗ {filename} не найден")

print("\nГотово! Все файлы исправлены.")