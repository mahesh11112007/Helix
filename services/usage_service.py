from datetime import datetime, date
from services.db_service import db_service

class UsageService:
    def __init__(self):
        # Define limits
        self.LIMITS = {
            "free": {
                "study_decks": 5,
                "planner_commands": 3,
                "daily_chats": 5
            },
            "premium": {
                "study_decks": 999999,
                "planner_commands": 999999,
                "daily_chats": 999999
            }
        }

    def _ensure_usage_record(self, user_id):
        record = db_service.query("SELECT * FROM user_usage WHERE user_id = ?", (user_id,), one=True)
        if not record:
            db_service.execute("INSERT INTO user_usage (user_id) VALUES (?)", (user_id,))
            record = db_service.query("SELECT * FROM user_usage WHERE user_id = ?", (user_id,), one=True)
        
        # Reset daily chats if it's a new day
        today_str = date.today().isoformat()
        if record["last_chat_date"] != today_str:
            db_service.execute(
                "UPDATE user_usage SET daily_chats = 0, last_chat_date = ? WHERE user_id = ?",
                (today_str, user_id)
            )
            # Re-fetch or manually update dict to avoid sqlite3.Row immutability issues
            record = db_service.query("SELECT * FROM user_usage WHERE user_id = ?", (user_id,), one=True)
            
        return record

    def get_tier(self, user_id):
        record = self._ensure_usage_record(user_id)
        return record["subscription_tier"]

    def can_generate_deck(self, user_id):
        record = self._ensure_usage_record(user_id)
        tier = record["subscription_tier"]
        return record["study_decks_generated"] < self.LIMITS[tier]["study_decks"]

    def increment_deck(self, user_id):
        db_service.execute("UPDATE user_usage SET study_decks_generated = study_decks_generated + 1 WHERE user_id = ?", (user_id,))

    def can_use_planner(self, user_id):
        record = self._ensure_usage_record(user_id)
        tier = record["subscription_tier"]
        return record["planner_commands_used"] < self.LIMITS[tier]["planner_commands"]

    def increment_planner(self, user_id):
        db_service.execute("UPDATE user_usage SET planner_commands_used = planner_commands_used + 1 WHERE user_id = ?", (user_id,))

    def can_chat(self, user_id):
        record = self._ensure_usage_record(user_id)
        tier = record["subscription_tier"]
        return record["daily_chats"] < self.LIMITS[tier]["daily_chats"]

    def increment_chat(self, user_id):
        self._ensure_usage_record(user_id) # ensure date is current
        db_service.execute("UPDATE user_usage SET daily_chats = daily_chats + 1 WHERE user_id = ?", (user_id,))

usage_service = UsageService()
