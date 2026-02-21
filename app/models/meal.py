"""Meal and food models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


class FoodItem(BaseModel):
    """Individual food item with nutritional info."""

    name: str
    portion: str
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0


class Meal(BaseModel):
    """A single meal (breakfast, lunch, dinner, or snack)."""

    name: str
    description: Optional[str] = None
    ingredients: List[FoodItem] = []
    recipe: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    estimated_cost: Optional[float] = None


class MealPlanMeals(BaseModel):
    """Structure for all meals in a day."""

    breakfast: Meal
    lunch: Meal
    dinner: Meal
    snacks: List[Meal] = []


class ShoppingItem(BaseModel):
    """Item for shopping list."""

    name: str
    quantity: str
    estimated_cost: Optional[float] = None
    category: Optional[str] = None  # produce, dairy, meat, etc.


class MealPlan(BaseModel):
    """Daily meal plan."""

    id: UUID
    user_id: UUID
    plan_date: date
    meals: MealPlanMeals
    shopping_list: List[ShoppingItem] = []
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    estimated_cost: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MealPlanCreate(BaseModel):
    """Data for creating a meal plan."""

    user_id: UUID
    plan_date: date
    meals: dict
    shopping_list: List[dict] = []
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    estimated_cost: Optional[float] = None
