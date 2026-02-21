"""Nutrition calculations and formulas."""

from typing import Literal, Optional, Dict
from dataclasses import dataclass


@dataclass
class NutritionTargets:
    """Daily nutrition targets."""

    calories: int
    protein: int
    carbs: int
    fat: int


class NutritionCalculator:
    """Calculate BMR, TDEE, and macro targets."""

    # Activity level multipliers
    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,      # Little or no exercise
        "light": 1.375,         # Light exercise 1-3 days/week
        "moderate": 1.55,       # Moderate exercise 3-5 days/week
        "active": 1.725,        # Hard exercise 6-7 days/week
        "very_active": 1.9,     # Very hard exercise, physical job
    }

    # Goal adjustments (calorie multiplier)
    GOAL_ADJUSTMENTS = {
        "weight_loss": 0.80,           # 20% deficit
        "muscle_gain": 1.15,           # 15% surplus
        "maintenance": 1.0,            # No change
        "keto": 0.85,                  # Slight deficit, high fat
        "intermittent_fasting": 0.90,  # 10% deficit
    }

    # Macro ratios by goal (protein%, carbs%, fat%)
    MACRO_RATIOS = {
        "weight_loss": (0.35, 0.35, 0.30),
        "muscle_gain": (0.30, 0.45, 0.25),
        "maintenance": (0.25, 0.50, 0.25),
        "keto": (0.25, 0.05, 0.70),
        "intermittent_fasting": (0.30, 0.40, 0.30),
    }

    @staticmethod
    def calculate_bmr(
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: Literal["male", "female", "other"]
    ) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.

        For "other" gender, we use average of male and female formulas.
        """
        if gender == "male":
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        elif gender == "female":
            bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        else:
            # Average of male and female
            male_bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
            female_bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
            bmr = (male_bmr + female_bmr) / 2

        return round(bmr)

    @classmethod
    def calculate_tdee(
        cls,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: Literal["male", "female", "other"],
        activity_level: str
    ) -> int:
        """Calculate Total Daily Energy Expenditure."""
        bmr = cls.calculate_bmr(weight_kg, height_cm, age, gender)
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
        return round(bmr * multiplier)

    @classmethod
    def calculate_targets(
        cls,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: Literal["male", "female", "other"],
        activity_level: str,
        goal_type: str,
        custom_calories: Optional[int] = None,
    ) -> NutritionTargets:
        """
        Calculate daily nutrition targets based on user profile and goals.

        Returns calories, protein, carbs, and fat targets.
        """
        # Calculate TDEE
        tdee = cls.calculate_tdee(weight_kg, height_cm, age, gender, activity_level)

        # Apply goal adjustment
        adjustment = cls.GOAL_ADJUSTMENTS.get(goal_type, 1.0)
        target_calories = custom_calories or round(tdee * adjustment)

        # Get macro ratios
        protein_ratio, carbs_ratio, fat_ratio = cls.MACRO_RATIOS.get(
            goal_type, (0.25, 0.50, 0.25)
        )

        # Calculate macros (protein & carbs = 4 cal/g, fat = 9 cal/g)
        protein = round((target_calories * protein_ratio) / 4)
        carbs = round((target_calories * carbs_ratio) / 4)
        fat = round((target_calories * fat_ratio) / 9)

        return NutritionTargets(
            calories=target_calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
        )

    @staticmethod
    def calculate_water_target(weight_kg: float, activity_level: str) -> int:
        """
        Calculate daily water intake target in ml.

        Base: 30ml per kg of body weight
        Active: +500ml
        Very active: +1000ml
        """
        base_water = weight_kg * 30

        if activity_level == "active":
            base_water += 500
        elif activity_level == "very_active":
            base_water += 1000

        return round(base_water)

    @staticmethod
    def get_meal_distribution(meal_frequency: int, goal_type: str) -> Dict[str, float]:
        """
        Get calorie distribution across meals.

        Returns percentage of daily calories for each meal.
        """
        if goal_type == "intermittent_fasting":
            # 16:8 pattern - no breakfast
            if meal_frequency >= 3:
                return {
                    "lunch": 0.45,
                    "dinner": 0.45,
                    "snacks": 0.10,
                }
            else:
                return {
                    "lunch": 0.50,
                    "dinner": 0.50,
                }

        if meal_frequency == 1:  # OMAD
            return {"dinner": 1.0}
        elif meal_frequency == 2:
            return {"lunch": 0.45, "dinner": 0.55}
        elif meal_frequency == 3:
            return {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}
        elif meal_frequency == 4:
            return {"breakfast": 0.20, "lunch": 0.30, "dinner": 0.35, "snacks": 0.15}
        elif meal_frequency >= 5:
            return {
                "breakfast": 0.20,
                "mid_morning_snack": 0.10,
                "lunch": 0.25,
                "afternoon_snack": 0.10,
                "dinner": 0.30,
                "evening_snack": 0.05,
            }

        return {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}

    @staticmethod
    def estimate_food_nutrition(food_description: str) -> Dict[str, int]:
        """
        Estimate nutrition from food description (rule-based fallback).

        This is a simple estimation when AI is not available.
        Returns approximate calories, protein, carbs, fat.
        """
        food_lower = food_description.lower()

        # Common food estimates per serving
        estimates = {
            # Proteins
            "chicken": {"calories": 165, "protein": 31, "carbs": 0, "fat": 4},
            "beef": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15},
            "fish": {"calories": 150, "protein": 25, "carbs": 0, "fat": 5},
            "egg": {"calories": 78, "protein": 6, "carbs": 1, "fat": 5},
            "tofu": {"calories": 80, "protein": 8, "carbs": 2, "fat": 4},

            # Carbs
            "rice": {"calories": 200, "protein": 4, "carbs": 45, "fat": 0},
            "bread": {"calories": 80, "protein": 3, "carbs": 15, "fat": 1},
            "pasta": {"calories": 220, "protein": 8, "carbs": 43, "fat": 1},
            "potato": {"calories": 160, "protein": 4, "carbs": 37, "fat": 0},
            "oatmeal": {"calories": 150, "protein": 5, "carbs": 27, "fat": 3},

            # Dairy
            "milk": {"calories": 150, "protein": 8, "carbs": 12, "fat": 8},
            "yogurt": {"calories": 100, "protein": 10, "carbs": 6, "fat": 3},
            "cheese": {"calories": 110, "protein": 7, "carbs": 0, "fat": 9},

            # Vegetables
            "salad": {"calories": 50, "protein": 2, "carbs": 10, "fat": 0},
            "vegetables": {"calories": 50, "protein": 2, "carbs": 10, "fat": 0},
            "broccoli": {"calories": 55, "protein": 4, "carbs": 11, "fat": 1},

            # Fruits
            "apple": {"calories": 95, "protein": 0, "carbs": 25, "fat": 0},
            "banana": {"calories": 105, "protein": 1, "carbs": 27, "fat": 0},
            "orange": {"calories": 62, "protein": 1, "carbs": 15, "fat": 0},

            # Common meals
            "sandwich": {"calories": 350, "protein": 15, "carbs": 40, "fat": 15},
            "burger": {"calories": 500, "protein": 25, "carbs": 40, "fat": 25},
            "pizza": {"calories": 285, "protein": 12, "carbs": 36, "fat": 10},
            "salad bowl": {"calories": 300, "protein": 15, "carbs": 30, "fat": 12},
            "smoothie": {"calories": 250, "protein": 8, "carbs": 45, "fat": 5},

            # Snacks
            "nuts": {"calories": 170, "protein": 5, "carbs": 6, "fat": 15},
            "protein bar": {"calories": 200, "protein": 20, "carbs": 20, "fat": 8},
            "cookie": {"calories": 150, "protein": 2, "carbs": 20, "fat": 7},
        }

        # Find matching food
        for food, nutrition in estimates.items():
            if food in food_lower:
                return nutrition

        # Default estimate for unknown foods
        return {"calories": 200, "protein": 10, "carbs": 25, "fat": 8}
