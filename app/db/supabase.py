"""Supabase client and database operations."""

from supabase import create_client, Client
from functools import lru_cache
from typing import Optional, List
from datetime import date, datetime, timedelta
from uuid import UUID

from app.config import get_settings
from app.models.user import User, UserCreate, UserUpdate, UserSettings
from app.models.meal import MealPlan, MealPlanCreate
from app.models.tracking import FoodLog, FoodLogCreate, WeightLog, WeightLogCreate, WaterLog, WaterLogCreate, Streak


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


class DatabaseService:
    """Database operations for Diet Agent."""

    def __init__(self):
        self.client = get_supabase_client()

    # User operations
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        result = self.client.table("users").insert(user_data.model_dump()).execute()
        user = User(**result.data[0])

        # Create default settings
        self.client.table("user_settings").insert({"user_id": str(user.id)}).execute()

        return user

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("telegram_id", telegram_id)
            .execute()
        )
        if result.data:
            return User(**result.data[0])
        return None

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = (
            self.client.table("users")
            .select("*")
            .eq("id", str(user_id))
            .execute()
        )
        if result.data:
            return User(**result.data[0])
        return None

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Update user profile."""
        update_data = user_data.model_dump(exclude_none=True)
        result = (
            self.client.table("users")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )
        return User(**result.data[0])

    def get_user_settings(self, user_id: UUID) -> Optional[UserSettings]:
        """Get user settings."""
        result = (
            self.client.table("user_settings")
            .select("*")
            .eq("user_id", str(user_id))
            .execute()
        )
        if result.data:
            return UserSettings(**result.data[0])
        return None

    def update_user_settings(self, user_id: UUID, settings: dict) -> UserSettings:
        """Update user settings."""
        result = (
            self.client.table("user_settings")
            .update(settings)
            .eq("user_id", str(user_id))
            .execute()
        )
        return UserSettings(**result.data[0])

    def get_all_users_with_notifications(self) -> List[User]:
        """Get all users with notifications enabled for scheduling."""
        result = (
            self.client.table("user_settings")
            .select("user_id")
            .eq("notifications_enabled", True)
            .execute()
        )
        user_ids = [r["user_id"] for r in result.data]

        if not user_ids:
            return []

        users_result = (
            self.client.table("users")
            .select("*")
            .in_("id", user_ids)
            .execute()
        )
        return [User(**u) for u in users_result.data]

    # Meal plan operations
    def create_meal_plan(self, plan_data: MealPlanCreate) -> MealPlan:
        """Create or update a meal plan for a date."""
        data = plan_data.model_dump()
        data["user_id"] = str(data["user_id"])
        data["plan_date"] = str(data["plan_date"])

        # Upsert - update if exists for that date
        result = (
            self.client.table("meal_plans")
            .upsert(data, on_conflict="user_id,plan_date")
            .execute()
        )
        return MealPlan(**result.data[0])

    def get_meal_plan(self, user_id: UUID, plan_date: date) -> Optional[MealPlan]:
        """Get meal plan for a specific date."""
        result = (
            self.client.table("meal_plans")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("plan_date", str(plan_date))
            .execute()
        )
        if result.data:
            return MealPlan(**result.data[0])
        return None

    def get_recent_meal_plans(self, user_id: UUID, days: int = 7) -> List[MealPlan]:
        """Get recent meal plans."""
        start_date = date.today() - timedelta(days=days)
        result = (
            self.client.table("meal_plans")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("plan_date", str(start_date))
            .order("plan_date", desc=True)
            .execute()
        )
        return [MealPlan(**p) for p in result.data]

    # Food log operations
    def create_food_log(self, user_id: UUID, log_data: FoodLogCreate) -> FoodLog:
        """Log food intake."""
        data = log_data.model_dump()
        data["user_id"] = str(user_id)
        result = self.client.table("food_logs").insert(data).execute()
        return FoodLog(**result.data[0])

    def get_food_logs_for_date(self, user_id: UUID, log_date: date) -> List[FoodLog]:
        """Get all food logs for a specific date."""
        start = datetime.combine(log_date, datetime.min.time())
        end = datetime.combine(log_date, datetime.max.time())

        result = (
            self.client.table("food_logs")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("logged_at", start.isoformat())
            .lte("logged_at", end.isoformat())
            .order("logged_at")
            .execute()
        )
        return [FoodLog(**log) for log in result.data]

    def get_daily_totals(self, user_id: UUID, log_date: date) -> dict:
        """Calculate daily nutrition totals."""
        logs = self.get_food_logs_for_date(user_id, log_date)
        return {
            "calories": sum(log.calories for log in logs),
            "protein": sum(log.protein for log in logs),
            "carbs": sum(log.carbs for log in logs),
            "fat": sum(log.fat for log in logs),
            "meals_logged": len(logs),
        }

    # Weight log operations
    def create_weight_log(self, user_id: UUID, log_data: WeightLogCreate) -> WeightLog:
        """Log weight."""
        data = log_data.model_dump()
        data["user_id"] = str(user_id)
        result = self.client.table("weight_logs").insert(data).execute()
        return WeightLog(**result.data[0])

    def get_weight_history(self, user_id: UUID, days: int = 30) -> List[WeightLog]:
        """Get weight history."""
        start_date = datetime.now() - timedelta(days=days)
        result = (
            self.client.table("weight_logs")
            .select("*")
            .eq("user_id", str(user_id))
            .gte("logged_at", start_date.isoformat())
            .order("logged_at", desc=True)
            .execute()
        )
        return [WeightLog(**log) for log in result.data]

    def get_latest_weight(self, user_id: UUID) -> Optional[WeightLog]:
        """Get most recent weight log."""
        result = (
            self.client.table("weight_logs")
            .select("*")
            .eq("user_id", str(user_id))
            .order("logged_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return WeightLog(**result.data[0])
        return None

    # Water log operations
    def create_water_log(self, user_id: UUID, log_data: WaterLogCreate) -> WaterLog:
        """Log water intake."""
        data = log_data.model_dump()
        data["user_id"] = str(user_id)
        result = self.client.table("water_logs").insert(data).execute()
        return WaterLog(**result.data[0])

    def get_daily_water(self, user_id: UUID, log_date: date) -> int:
        """Get total water intake for a date in ml."""
        start = datetime.combine(log_date, datetime.min.time())
        end = datetime.combine(log_date, datetime.max.time())

        result = (
            self.client.table("water_logs")
            .select("amount_ml")
            .eq("user_id", str(user_id))
            .gte("logged_at", start.isoformat())
            .lte("logged_at", end.isoformat())
            .execute()
        )
        return sum(log["amount_ml"] for log in result.data)

    # Streak operations
    def get_streak(self, user_id: UUID, streak_type: str) -> Optional[Streak]:
        """Get streak for a user."""
        result = (
            self.client.table("streaks")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("streak_type", streak_type)
            .execute()
        )
        if result.data:
            return Streak(**result.data[0])
        return None

    def update_streak(self, user_id: UUID, streak_type: str) -> Streak:
        """Update streak for today's activity."""
        today = date.today()
        streak = self.get_streak(user_id, streak_type)

        if streak:
            last_date = streak.last_activity_date.date() if streak.last_activity_date else None

            if last_date == today:
                # Already updated today
                return streak
            elif last_date == today - timedelta(days=1):
                # Continue streak
                new_streak = streak.current_streak + 1
                longest = max(streak.longest_streak, new_streak)
            else:
                # Streak broken, start over
                new_streak = 1
                longest = streak.longest_streak

            result = (
                self.client.table("streaks")
                .update({
                    "current_streak": new_streak,
                    "longest_streak": longest,
                    "last_activity_date": today.isoformat(),
                })
                .eq("id", str(streak.id))
                .execute()
            )
            return Streak(**result.data[0])
        else:
            # Create new streak
            result = (
                self.client.table("streaks")
                .insert({
                    "user_id": str(user_id),
                    "streak_type": streak_type,
                    "current_streak": 1,
                    "longest_streak": 1,
                    "last_activity_date": today.isoformat(),
                })
                .execute()
            )
            return Streak(**result.data[0])
