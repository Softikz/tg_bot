# --- В DB добавляем эти методы ---
def reset_user_progress(self, user_id: int):
    """Сбрасывает баланс и улучшения пользователя."""
    cur = self.conn.cursor()
    cur.execute("""
        UPDATE users
        SET bananas=0,
            per_click=1,
            per_second=0,
            upgrades='{}'
        WHERE user_id=?
    """, (user_id,))
    self.conn.commit()

def add_gold_banana(self, user_id: int, amount: int = 1):
    """Добавляет золотой банан пользователю."""
    user = self.get_user(user_id)
    gold_expires = max(time.time(), user.get("gold_expires", 0)) + 86400  # 1 день
    self.update_user(user_id, gold_expires=gold_expires)

def add_passive_clicks(self, user_id: int, amount: int = 2):
    """Добавляет пассив к пользователю."""
    user = self.get_user(user_id)
    self.update_user(user_id, per_second=user.get("per_second", 0) + amount)

def add_bananas(self, user_id: int, amount: int):
    """Накрутка бананов (для себя)."""
    user = self.get_user(user_id)
    self.update_user(user_id, bananas=user.get("bananas", 0) + amount)
