"""AI-powered meal planning with multiple provider support."""

import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date
import random

from app.config import get_settings
from app.models.user import User
from app.models.meal import Meal, MealPlanMeals, ShoppingItem
from app.services.nutrition import NutritionCalculator


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate_meal_plan(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> Dict[str, Any]:
        """Generate a meal plan using the AI provider."""
        pass

    @abstractmethod
    async def parse_food_log(
        self,
        food_description: str,
    ) -> Dict[str, int]:
        """Parse natural language food description to nutrition values."""
        pass

    @abstractmethod
    async def get_meal_suggestion(
        self,
        user: User,
        meal_type: str,
        remaining_calories: int,
    ) -> Meal:
        """Get a quick meal suggestion."""
        pass


class OllamaProvider(AIProvider):
    """Ollama (local LLM) provider."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.ollama_host
        self.model = settings.ollama_model

    async def _query(self, prompt: str) -> str:
        """Query Ollama API."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_meal_plan(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> Dict[str, Any]:
        prompt = self._build_meal_plan_prompt(
            user, target_calories, restrictions, cuisine_preferences, recent_meals
        )
        response = await self._query(prompt)
        return json.loads(response)

    async def parse_food_log(self, food_description: str) -> Dict[str, int]:
        prompt = f"""Estimate the nutritional content of this food:
"{food_description}"

Return JSON with: {{"calories": int, "protein": int, "carbs": int, "fat": int}}
Only return the JSON, nothing else."""

        response = await self._query(prompt)
        return json.loads(response)

    async def get_meal_suggestion(
        self, user: User, meal_type: str, remaining_calories: int
    ) -> Meal:
        restrictions_str = ", ".join(user.restrictions) if user.restrictions else "none"
        cuisines_str = ", ".join(user.cuisine_preferences) if user.cuisine_preferences else "any"

        prompt = f"""Suggest a {meal_type} meal with approximately {remaining_calories} calories.
Restrictions: {restrictions_str}
Preferred cuisines: {cuisines_str}
Budget: {user.budget}

Return JSON: {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int}}"""

        response = await self._query(prompt)
        data = json.loads(response)
        return Meal(**data)

    def _build_meal_plan_prompt(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> str:
        restrictions_str = ", ".join(restrictions) if restrictions else "none"
        cuisines_str = ", ".join(cuisine_preferences) if cuisine_preferences else "any"
        recent_str = ", ".join(recent_meals[-10:]) if recent_meals else "none"

        return f"""Create a daily meal plan with these requirements:
- Total calories: {target_calories}
- Meals per day: {user.meal_frequency}
- Dietary restrictions: {restrictions_str}
- Preferred cuisines: {cuisines_str}
- Budget: {user.budget}
- Avoid repeating these recent meals: {recent_str}

Return a JSON object with this structure:
{{
    "breakfast": {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int, "ingredients": [str]}},
    "lunch": {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int, "ingredients": [str]}},
    "dinner": {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int, "ingredients": [str]}},
    "snacks": [{{"name": str, "calories": int, "protein": int, "carbs": int, "fat": int}}],
    "shopping_list": [{{"name": str, "quantity": str, "category": str}}]
}}

Make sure total calories match the target. Only return the JSON."""


class GroqProvider(AIProvider):
    """Groq cloud provider (free tier)."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.groq_api_key

    async def _query(self, prompt: str) -> str:
        """Query Groq API."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def generate_meal_plan(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> Dict[str, Any]:
        prompt = self._build_meal_plan_prompt(
            user, target_calories, restrictions, cuisine_preferences, recent_meals
        )
        response = await self._query(prompt)
        return json.loads(response)

    async def parse_food_log(self, food_description: str) -> Dict[str, int]:
        prompt = f"""Estimate the nutritional content of this food:
"{food_description}"

Return JSON with: {{"calories": int, "protein": int, "carbs": int, "fat": int}}"""

        response = await self._query(prompt)
        return json.loads(response)

    async def get_meal_suggestion(
        self, user: User, meal_type: str, remaining_calories: int
    ) -> Meal:
        restrictions_str = ", ".join(user.restrictions) if user.restrictions else "none"
        cuisines_str = ", ".join(user.cuisine_preferences) if user.cuisine_preferences else "any"

        prompt = f"""Suggest a {meal_type} meal with approximately {remaining_calories} calories.
Restrictions: {restrictions_str}
Preferred cuisines: {cuisines_str}

Return JSON: {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int}}"""

        response = await self._query(prompt)
        data = json.loads(response)
        return Meal(**data)

    _build_meal_plan_prompt = OllamaProvider._build_meal_plan_prompt


class GeminiProvider(AIProvider):
    """Google Gemini provider (free tier)."""

    def __init__(self):
        import google.generativeai as genai
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def _query(self, prompt: str) -> str:
        """Query Gemini API."""
        response = await self.model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return response.text

    async def generate_meal_plan(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> Dict[str, Any]:
        prompt = OllamaProvider._build_meal_plan_prompt(
            self, user, target_calories, restrictions, cuisine_preferences, recent_meals
        )
        response = await self._query(prompt)
        return json.loads(response)

    async def parse_food_log(self, food_description: str) -> Dict[str, int]:
        prompt = f"""Estimate the nutritional content of this food:
"{food_description}"

Return JSON with: {{"calories": int, "protein": int, "carbs": int, "fat": int}}"""

        response = await self._query(prompt)
        return json.loads(response)

    async def get_meal_suggestion(
        self, user: User, meal_type: str, remaining_calories: int
    ) -> Meal:
        restrictions_str = ", ".join(user.restrictions) if user.restrictions else "none"
        cuisines_str = ", ".join(user.cuisine_preferences) if user.cuisine_preferences else "any"

        prompt = f"""Suggest a {meal_type} meal with approximately {remaining_calories} calories.
Restrictions: {restrictions_str}
Preferred cuisines: {cuisines_str}

Return JSON: {{"name": str, "description": str, "calories": int, "protein": int, "carbs": int, "fat": int, "prep_time_minutes": int}}"""

        response = await self._query(prompt)
        data = json.loads(response)
        return Meal(**data)


class RuleBasedProvider(AIProvider):
    """Rule-based meal planning (no AI, completely free)."""

    # Meal templates by cuisine
    MEAL_TEMPLATES = {
        "breakfast": [
            {"name": "Oatmeal with Berries", "calories": 350, "protein": 12, "carbs": 55, "fat": 8, "cuisines": ["american", "any"]},
            {"name": "Scrambled Eggs with Toast", "calories": 400, "protein": 20, "carbs": 30, "fat": 22, "cuisines": ["american", "any"]},
            {"name": "Greek Yogurt Parfait", "calories": 300, "protein": 18, "carbs": 40, "fat": 8, "cuisines": ["mediterranean", "any"]},
            {"name": "Avocado Toast", "calories": 320, "protein": 8, "carbs": 35, "fat": 18, "cuisines": ["american", "any"]},
            {"name": "Idli with Sambar", "calories": 280, "protein": 10, "carbs": 50, "fat": 4, "cuisines": ["indian"]},
            {"name": "Poha", "calories": 250, "protein": 6, "carbs": 45, "fat": 6, "cuisines": ["indian"]},
            {"name": "Smoothie Bowl", "calories": 380, "protein": 15, "carbs": 60, "fat": 10, "cuisines": ["any"]},
        ],
        "lunch": [
            {"name": "Grilled Chicken Salad", "calories": 450, "protein": 35, "carbs": 20, "fat": 25, "cuisines": ["american", "any"]},
            {"name": "Quinoa Buddha Bowl", "calories": 500, "protein": 18, "carbs": 65, "fat": 18, "cuisines": ["any"]},
            {"name": "Turkey Wrap", "calories": 420, "protein": 28, "carbs": 40, "fat": 16, "cuisines": ["american", "any"]},
            {"name": "Dal with Rice", "calories": 480, "protein": 16, "carbs": 70, "fat": 12, "cuisines": ["indian"]},
            {"name": "Mediterranean Bowl", "calories": 520, "protein": 22, "carbs": 55, "fat": 24, "cuisines": ["mediterranean"]},
            {"name": "Stir Fry with Tofu", "calories": 400, "protein": 20, "carbs": 45, "fat": 15, "cuisines": ["asian", "any"]},
            {"name": "Chicken Tikka with Roti", "calories": 550, "protein": 35, "carbs": 50, "fat": 20, "cuisines": ["indian"]},
        ],
        "dinner": [
            {"name": "Baked Salmon with Vegetables", "calories": 500, "protein": 40, "carbs": 25, "fat": 28, "cuisines": ["any"]},
            {"name": "Chicken Stir Fry", "calories": 480, "protein": 35, "carbs": 40, "fat": 18, "cuisines": ["asian", "any"]},
            {"name": "Vegetable Curry with Rice", "calories": 520, "protein": 14, "carbs": 75, "fat": 16, "cuisines": ["indian"]},
            {"name": "Grilled Steak with Sweet Potato", "calories": 600, "protein": 45, "carbs": 40, "fat": 28, "cuisines": ["american", "any"]},
            {"name": "Pasta Primavera", "calories": 480, "protein": 16, "carbs": 70, "fat": 14, "cuisines": ["italian", "any"]},
            {"name": "Fish Tacos", "calories": 450, "protein": 28, "carbs": 45, "fat": 18, "cuisines": ["mexican", "any"]},
            {"name": "Palak Paneer with Naan", "calories": 550, "protein": 22, "carbs": 55, "fat": 26, "cuisines": ["indian"]},
        ],
        "snacks": [
            {"name": "Apple with Almond Butter", "calories": 200, "protein": 5, "carbs": 25, "fat": 10, "cuisines": ["any"]},
            {"name": "Greek Yogurt", "calories": 150, "protein": 15, "carbs": 10, "fat": 5, "cuisines": ["any"]},
            {"name": "Mixed Nuts", "calories": 180, "protein": 5, "carbs": 8, "fat": 16, "cuisines": ["any"]},
            {"name": "Hummus with Veggies", "calories": 150, "protein": 6, "carbs": 15, "fat": 8, "cuisines": ["mediterranean", "any"]},
            {"name": "Protein Bar", "calories": 200, "protein": 20, "carbs": 22, "fat": 8, "cuisines": ["any"]},
            {"name": "Roasted Chickpeas", "calories": 130, "protein": 6, "carbs": 20, "fat": 3, "cuisines": ["indian", "any"]},
        ],
    }

    def _filter_by_restrictions(self, meals: List[Dict], restrictions: List[str]) -> List[Dict]:
        """Filter meals based on dietary restrictions."""
        if not restrictions:
            return meals

        filtered = []
        for meal in meals:
            name_lower = meal["name"].lower()
            excluded = False

            for restriction in restrictions:
                restriction_lower = restriction.lower()
                if restriction_lower in ["vegetarian", "vegan"]:
                    if any(word in name_lower for word in ["chicken", "beef", "fish", "salmon", "steak", "turkey", "meat"]):
                        excluded = True
                        break
                if restriction_lower == "vegan":
                    if any(word in name_lower for word in ["egg", "yogurt", "cheese", "paneer", "milk"]):
                        excluded = True
                        break
                if restriction_lower == "gluten-free":
                    if any(word in name_lower for word in ["bread", "toast", "pasta", "naan", "roti", "wrap"]):
                        excluded = True
                        break

            if not excluded:
                filtered.append(meal)

        return filtered if filtered else meals[:2]  # Return at least some options

    def _filter_by_cuisine(self, meals: List[Dict], preferences: List[str]) -> List[Dict]:
        """Filter meals based on cuisine preferences."""
        if not preferences:
            return meals

        filtered = []
        prefs_lower = [p.lower() for p in preferences]

        for meal in meals:
            meal_cuisines = [c.lower() for c in meal.get("cuisines", ["any"])]
            if "any" in meal_cuisines or any(p in meal_cuisines for p in prefs_lower):
                filtered.append(meal)

        return filtered if filtered else meals

    async def generate_meal_plan(
        self,
        user: User,
        target_calories: int,
        restrictions: List[str],
        cuisine_preferences: List[str],
        recent_meals: List[str],
    ) -> Dict[str, Any]:
        # Get meal distribution
        distribution = NutritionCalculator.get_meal_distribution(
            user.meal_frequency, user.goal_type or "maintenance"
        )

        result = {"shopping_list": []}

        # Generate each meal type
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meal_type not in distribution:
                continue

            target = int(target_calories * distribution.get(meal_type, 0))
            options = self.MEAL_TEMPLATES.get(meal_type, [])
            options = self._filter_by_restrictions(options, restrictions)
            options = self._filter_by_cuisine(options, cuisine_preferences)

            # Pick a random option, avoiding recent meals
            available = [m for m in options if m["name"] not in recent_meals]
            if not available:
                available = options

            meal = random.choice(available)
            result[meal_type] = {
                "name": meal["name"],
                "description": f"A healthy {meal_type} option",
                "calories": meal["calories"],
                "protein": meal["protein"],
                "carbs": meal["carbs"],
                "fat": meal["fat"],
                "prep_time_minutes": 20,
                "ingredients": [],
            }

        # Add snacks if needed
        snack_calories = int(target_calories * distribution.get("snacks", 0.1))
        if snack_calories > 0:
            snack_options = self._filter_by_restrictions(
                self.MEAL_TEMPLATES["snacks"], restrictions
            )
            snack = random.choice(snack_options)
            result["snacks"] = [{
                "name": snack["name"],
                "calories": snack["calories"],
                "protein": snack["protein"],
                "carbs": snack["carbs"],
                "fat": snack["fat"],
            }]
        else:
            result["snacks"] = []

        return result

    async def parse_food_log(self, food_description: str) -> Dict[str, int]:
        """Use simple estimation for food logging."""
        return NutritionCalculator.estimate_food_nutrition(food_description)

    async def get_meal_suggestion(
        self, user: User, meal_type: str, remaining_calories: int
    ) -> Meal:
        options = self.MEAL_TEMPLATES.get(meal_type, self.MEAL_TEMPLATES["snacks"])
        options = self._filter_by_restrictions(options, user.restrictions or [])
        options = self._filter_by_cuisine(options, user.cuisine_preferences or [])

        # Find option closest to remaining calories
        best = min(options, key=lambda m: abs(m["calories"] - remaining_calories))

        return Meal(
            name=best["name"],
            description=f"A healthy {meal_type} option",
            calories=best["calories"],
            protein=best["protein"],
            carbs=best["carbs"],
            fat=best["fat"],
            prep_time_minutes=15,
        )


class AIPlanner:
    """Main AI planner that uses configured provider."""

    def __init__(self, provider: Optional[str] = None):
        settings = get_settings()
        provider = provider or settings.ai_provider

        if provider == "ollama":
            self.provider = OllamaProvider()
        elif provider == "groq":
            self.provider = GroqProvider()
        elif provider == "gemini":
            self.provider = GeminiProvider()
        else:
            self.provider = RuleBasedProvider()

    async def generate_meal_plan(
        self,
        user: User,
        recent_meals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a daily meal plan for the user."""
        target_calories = user.target_calories or 2000
        restrictions = user.restrictions or []
        cuisine_preferences = user.cuisine_preferences or []
        recent = recent_meals or []

        try:
            return await self.provider.generate_meal_plan(
                user, target_calories, restrictions, cuisine_preferences, recent
            )
        except Exception as e:
            # Fallback to rule-based if AI fails
            print(f"AI provider failed, using rule-based fallback: {e}")
            fallback = RuleBasedProvider()
            return await fallback.generate_meal_plan(
                user, target_calories, restrictions, cuisine_preferences, recent
            )

    async def parse_food_log(self, food_description: str) -> Dict[str, int]:
        """Parse food description to nutrition values."""
        try:
            return await self.provider.parse_food_log(food_description)
        except Exception:
            # Fallback to estimation
            return NutritionCalculator.estimate_food_nutrition(food_description)

    async def get_meal_suggestion(
        self,
        user: User,
        meal_type: str = "snack",
        remaining_calories: int = 300,
    ) -> Meal:
        """Get a quick meal suggestion."""
        try:
            return await self.provider.get_meal_suggestion(user, meal_type, remaining_calories)
        except Exception:
            fallback = RuleBasedProvider()
            return await fallback.get_meal_suggestion(user, meal_type, remaining_calories)
