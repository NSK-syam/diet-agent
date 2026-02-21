"""User models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Data required to create a new user."""

    telegram_id: int
    username: Optional[str] = None
    name: Optional[str] = None


class UserUpdate(BaseModel):
    """Data for updating user profile."""

    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[Literal["male", "female", "other"]] = None
    height_cm: Optional[float] = Field(None, ge=50, le=300)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)
    activity_level: Optional[
        Literal["sedentary", "light", "moderate", "active", "very_active"]
    ] = None
    goal_type: Optional[
        Literal["weight_loss", "muscle_gain", "maintenance", "keto", "intermittent_fasting"]
    ] = None
    target_calories: Optional[int] = Field(None, ge=800, le=10000)
    target_protein: Optional[int] = Field(None, ge=0, le=500)
    target_carbs: Optional[int] = Field(None, ge=0, le=1000)
    target_fat: Optional[int] = Field(None, ge=0, le=500)
    restrictions: Optional[List[str]] = None
    cuisine_preferences: Optional[List[str]] = None
    meal_frequency: Optional[int] = Field(None, ge=1, le=8)
    budget: Optional[Literal["cheap", "moderate", "flexible"]] = None


class User(BaseModel):
    """Full user model."""

    id: UUID
    telegram_id: int
    username: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    goal_type: Optional[str] = None
    target_calories: Optional[int] = None
    target_protein: Optional[int] = None
    target_carbs: Optional[int] = None
    target_fat: Optional[int] = None
    restrictions: List[str] = []
    cuisine_preferences: List[str] = []
    meal_frequency: int = 3
    budget: str = "moderate"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User notification and preference settings."""

    id: UUID
    user_id: UUID
    ai_provider: str = "ollama"
    morning_plan_time: str = "07:00"
    evening_summary_time: str = "20:00"
    meal_reminder_times: List[str] = ["08:00", "12:00", "18:00"]
    enable_water_reminders: bool = False
    water_reminder_interval: int = 2
    notifications_enabled: bool = True
    timezone: str = "America/New_York"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
