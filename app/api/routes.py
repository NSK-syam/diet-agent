"""API routes for external integrations (Apple Health, Google Fit, etc.)."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.supabase import DatabaseService
from app.models.tracking import WaterLogCreate, WeightLogCreate, FoodLogCreate


router = APIRouter(prefix="/api/v1", tags=["Health Sync"])
db = DatabaseService()


class WaterSyncRequest(BaseModel):
    """Request to sync water intake from health apps."""
    telegram_id: int
    amount_ml: int
    timestamp: Optional[datetime] = None


class WeightSyncRequest(BaseModel):
    """Request to sync weight from health apps."""
    telegram_id: int
    weight_kg: float
    timestamp: Optional[datetime] = None


class FoodSyncRequest(BaseModel):
    """Request to sync food from health apps."""
    telegram_id: int
    food_description: str
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    meal_type: str = "other"


class SyncResponse(BaseModel):
    """Response for sync requests."""
    success: bool
    message: str
    daily_total: Optional[int] = None


@router.post("/sync/water", response_model=SyncResponse)
async def sync_water(request: WaterSyncRequest, x_api_key: str = Header(None)):
    """
    Sync water intake from Apple Health, Google Fit, or other apps.

    Use this endpoint with iOS Shortcuts or Tasker to auto-log water.

    Example iOS Shortcut:
    1. Create shortcut triggered by "Log Water to Health"
    2. Add "Get Contents of URL" action
    3. POST to http://your-server:8000/api/v1/sync/water
    4. Body: {"telegram_id": YOUR_ID, "amount_ml": 250}
    """
    user = db.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Start the bot first with /start")

    db.create_water_log(user.id, WaterLogCreate(amount_ml=request.amount_ml))
    db.update_streak(user.id, "water")

    from datetime import date
    daily_total = db.get_daily_water(user.id, date.today())

    return SyncResponse(
        success=True,
        message=f"Logged {request.amount_ml}ml of water",
        daily_total=daily_total
    )


@router.post("/sync/weight", response_model=SyncResponse)
async def sync_weight(request: WeightSyncRequest, x_api_key: str = Header(None)):
    """
    Sync weight from Apple Health, Google Fit, or smart scales.

    Example: Withings/Fitbit webhook can POST here to auto-log weight.
    """
    user = db.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.create_weight_log(user.id, WeightLogCreate(weight_kg=request.weight_kg))

    from app.models.user import UserUpdate
    db.update_user(user.id, UserUpdate(weight_kg=request.weight_kg))

    return SyncResponse(
        success=True,
        message=f"Logged weight: {request.weight_kg}kg"
    )


@router.post("/sync/food", response_model=SyncResponse)
async def sync_food(request: FoodSyncRequest, x_api_key: str = Header(None)):
    """
    Sync food intake from other apps like MyFitnessPal.
    """
    user = db.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.create_food_log(user.id, FoodLogCreate(
        meal_type=request.meal_type,
        food_description=request.food_description,
        calories=request.calories,
        protein=request.protein,
        carbs=request.carbs,
        fat=request.fat,
    ))

    db.update_streak(user.id, "logging")

    from datetime import date
    totals = db.get_daily_totals(user.id, date.today())

    return SyncResponse(
        success=True,
        message=f"Logged: {request.food_description}",
        daily_total=totals["calories"]
    )


@router.get("/user/{telegram_id}/stats")
async def get_user_stats(telegram_id: int):
    """Get user's daily stats for health app widgets."""
    user = db.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from datetime import date
    from app.services.nutrition import NutritionCalculator

    totals = db.get_daily_totals(user.id, date.today())
    water = db.get_daily_water(user.id, date.today())
    water_target = NutritionCalculator.calculate_water_target(
        user.weight_kg or 70,
        user.activity_level or "moderate"
    )

    return {
        "calories": {
            "consumed": totals["calories"],
            "target": user.target_calories or 2000,
            "remaining": (user.target_calories or 2000) - totals["calories"]
        },
        "protein": {
            "consumed": totals["protein"],
            "target": user.target_protein or 150
        },
        "water": {
            "consumed_ml": water,
            "target_ml": water_target,
            "percentage": round(water / water_target * 100) if water_target else 0
        },
        "meals_logged": totals["meals_logged"]
    }
