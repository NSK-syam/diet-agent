"""Tracking models for food, weight, water, and streaks."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class FoodLogCreate(BaseModel):
    """Data for logging food."""

    meal_type: Literal["breakfast", "lunch", "dinner", "snack", "other"]
    food_description: str
    portion_size: Optional[str] = None
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    photo_url: Optional[str] = None
    notes: Optional[str] = None


class FoodLog(BaseModel):
    """Food log entry."""

    id: UUID
    user_id: UUID
    logged_at: datetime
    meal_type: str
    food_description: str
    portion_size: Optional[str] = None
    calories: int
    protein: int
    carbs: int
    fat: int
    photo_url: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class WeightLogCreate(BaseModel):
    """Data for logging weight."""

    weight_kg: float = Field(ge=20, le=500)
    notes: Optional[str] = None


class WeightLog(BaseModel):
    """Weight log entry."""

    id: UUID
    user_id: UUID
    logged_at: datetime
    weight_kg: float
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class WaterLogCreate(BaseModel):
    """Data for logging water intake."""

    amount_ml: int = 250  # Default glass of water


class WaterLog(BaseModel):
    """Water intake log entry."""

    id: UUID
    user_id: UUID
    logged_at: datetime
    amount_ml: int

    class Config:
        from_attributes = True


class Streak(BaseModel):
    """Streak tracking for motivation."""

    id: UUID
    user_id: UUID
    streak_type: Literal["logging", "plan_following", "water"]
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class DailyProgress(BaseModel):
    """Daily progress summary."""

    date: datetime
    calories_consumed: int
    calories_target: int
    protein_consumed: int
    protein_target: int
    carbs_consumed: int
    carbs_target: int
    fat_consumed: int
    fat_target: int
    water_ml: int
    meals_logged: int
    on_track: bool


class WeeklyReport(BaseModel):
    """Weekly progress report."""

    start_date: datetime
    end_date: datetime
    avg_calories: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    weight_change: Optional[float] = None
    days_on_track: int
    total_days: int
    logging_streak: int
    recommendations: list[str] = []
