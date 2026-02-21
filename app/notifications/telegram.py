"""Telegram bot for Diet Agent."""

import asyncio
from datetime import date, datetime
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from app.config import get_settings
from app.db.supabase import DatabaseService
from app.models.user import UserCreate, UserUpdate
from app.models.tracking import FoodLogCreate, WeightLogCreate, WaterLogCreate
from app.models.meal import MealPlanCreate
from app.services.nutrition import NutritionCalculator
from app.services.ai_planner import AIPlanner
from app.services.goal_tracker import GoalTracker


# Conversation states
(
    NAME, AGE, GENDER, HEIGHT, WEIGHT,
    ACTIVITY, GOAL, RESTRICTIONS, CUISINE, DONE
) = range(10)


class TelegramBot:
    """Telegram bot handler for Diet Agent."""

    def __init__(self):
        self.settings = get_settings()
        self.db = DatabaseService()
        self.tracker = GoalTracker()
        self.app: Optional[Application] = None

    def create_application(self) -> Application:
        """Create and configure the Telegram application."""
        self.app = (
            Application.builder()
            .token(self.settings.telegram_bot_token)
            .build()
        )

        # Add conversation handler for onboarding
        onboarding_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_age)],
                GENDER: [CallbackQueryHandler(self.get_gender)],
                HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_height)],
                WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_weight)],
                ACTIVITY: [CallbackQueryHandler(self.get_activity)],
                GOAL: [CallbackQueryHandler(self.get_goal)],
                RESTRICTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_restrictions)],
                CUISINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_cuisine)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        # Add handlers
        self.app.add_handler(onboarding_handler)
        self.app.add_handler(CommandHandler("plan", self.plan_command))
        self.app.add_handler(CommandHandler("log", self.log_command))
        self.app.add_handler(CommandHandler("quick", self.quick_log_command))
        self.app.add_handler(CommandHandler("suggest", self.suggest_command))
        self.app.add_handler(CommandHandler("snack", self.snack_command))
        self.app.add_handler(CommandHandler("water", self.water_command))
        self.app.add_handler(CommandHandler("progress", self.progress_command))
        self.app.add_handler(CommandHandler("goals", self.goals_command))
        self.app.add_handler(CommandHandler("avoid", self.avoid_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("weight", self.weight_command))

        # Callback handlers for inline keyboards
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        return self.app

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command - begin onboarding."""
        telegram_id = update.effective_user.id

        # Check if user exists
        existing = self.db.get_user_by_telegram_id(telegram_id)
        if existing and existing.name:
            await update.message.reply_text(
                f"Welcome back, {existing.name}!\n\n"
                "Use /plan to see today's meal plan\n"
                "Use /help to see all commands"
            )
            return ConversationHandler.END

        # Create or update user
        if not existing:
            self.db.create_user(UserCreate(
                telegram_id=telegram_id,
                username=update.effective_user.username,
            ))

        await update.message.reply_text(
            "Welcome to Diet Agent!\n\n"
            "I'll help you plan meals, track nutrition, and reach your health goals.\n\n"
            "Let's set up your profile. What's your name?"
        )
        return NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's name."""
        context.user_data["name"] = update.message.text.strip()
        await update.message.reply_text(
            f"Nice to meet you, {context.user_data['name']}!\n\n"
            "How old are you? (Enter a number)"
        )
        return AGE

    async def get_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's age."""
        try:
            age = int(update.message.text.strip())
            if age < 10 or age > 120:
                raise ValueError()
            context.user_data["age"] = age
        except ValueError:
            await update.message.reply_text("Please enter a valid age (10-120):")
            return AGE

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Male", callback_data="gender_male")],
            [InlineKeyboardButton("Female", callback_data="gender_female")],
            [InlineKeyboardButton("Other", callback_data="gender_other")],
        ])
        await update.message.reply_text("What's your gender?", reply_markup=keyboard)
        return GENDER

    async def get_gender(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's gender."""
        query = update.callback_query
        await query.answer()

        gender = query.data.replace("gender_", "")
        context.user_data["gender"] = gender

        await query.edit_message_text(
            f"Gender: {gender.title()}\n\n"
            "What's your height in cm? (e.g., 175)"
        )
        return HEIGHT

    async def get_height(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's height."""
        try:
            height = float(update.message.text.strip())
            if height < 50 or height > 300:
                raise ValueError()
            context.user_data["height_cm"] = height
        except ValueError:
            await update.message.reply_text("Please enter a valid height in cm (50-300):")
            return HEIGHT

        await update.message.reply_text("What's your current weight in kg? (e.g., 70)")
        return WEIGHT

    async def get_weight(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's weight."""
        try:
            weight = float(update.message.text.strip())
            if weight < 20 or weight > 500:
                raise ValueError()
            context.user_data["weight_kg"] = weight
        except ValueError:
            await update.message.reply_text("Please enter a valid weight in kg (20-500):")
            return WEIGHT

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Sedentary (desk job)", callback_data="activity_sedentary")],
            [InlineKeyboardButton("Light (1-3 days/week)", callback_data="activity_light")],
            [InlineKeyboardButton("Moderate (3-5 days/week)", callback_data="activity_moderate")],
            [InlineKeyboardButton("Active (6-7 days/week)", callback_data="activity_active")],
            [InlineKeyboardButton("Very Active (physical job)", callback_data="activity_very_active")],
        ])
        await update.message.reply_text(
            "How active are you?",
            reply_markup=keyboard
        )
        return ACTIVITY

    async def get_activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's activity level."""
        query = update.callback_query
        await query.answer()

        activity = query.data.replace("activity_", "")
        context.user_data["activity_level"] = activity

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Lose Weight", callback_data="goal_weight_loss")],
            [InlineKeyboardButton("Build Muscle", callback_data="goal_muscle_gain")],
            [InlineKeyboardButton("Maintain Weight", callback_data="goal_maintenance")],
            [InlineKeyboardButton("Keto Diet", callback_data="goal_keto")],
            [InlineKeyboardButton("Intermittent Fasting", callback_data="goal_intermittent_fasting")],
        ])
        await query.edit_message_text(
            "What's your primary goal?",
            reply_markup=keyboard
        )
        return GOAL

    async def get_goal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's goal."""
        query = update.callback_query
        await query.answer()

        goal = query.data.replace("goal_", "")
        context.user_data["goal_type"] = goal

        await query.edit_message_text(
            "Any dietary restrictions?\n\n"
            "Enter them separated by commas (e.g., vegetarian, gluten-free, nut allergy)\n"
            "Or type 'none' if you don't have any:"
        )
        return RESTRICTIONS

    async def get_restrictions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's dietary restrictions."""
        text = update.message.text.strip().lower()

        if text == "none":
            context.user_data["restrictions"] = []
        else:
            restrictions = [r.strip() for r in text.split(",") if r.strip()]
            context.user_data["restrictions"] = restrictions

        await update.message.reply_text(
            "What cuisines do you prefer?\n\n"
            "Enter them separated by commas (e.g., Indian, Mediterranean, Asian)\n"
            "Or type 'any' for no preference:"
        )
        return CUISINE

    async def get_cuisine(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get user's cuisine preferences and finish setup."""
        text = update.message.text.strip().lower()

        if text == "any":
            context.user_data["cuisine_preferences"] = []
        else:
            cuisines = [c.strip().title() for c in text.split(",") if c.strip()]
            context.user_data["cuisine_preferences"] = cuisines

        # Calculate nutrition targets
        targets = NutritionCalculator.calculate_targets(
            weight_kg=context.user_data["weight_kg"],
            height_cm=context.user_data["height_cm"],
            age=context.user_data["age"],
            gender=context.user_data["gender"],
            activity_level=context.user_data["activity_level"],
            goal_type=context.user_data["goal_type"],
        )

        context.user_data["target_calories"] = targets.calories
        context.user_data["target_protein"] = targets.protein
        context.user_data["target_carbs"] = targets.carbs
        context.user_data["target_fat"] = targets.fat

        # Update user in database
        telegram_id = update.effective_user.id
        user = self.db.get_user_by_telegram_id(telegram_id)

        self.db.update_user(user.id, UserUpdate(**context.user_data))

        # Log initial weight
        self.db.create_weight_log(user.id, WeightLogCreate(
            weight_kg=context.user_data["weight_kg"]
        ))

        await update.message.reply_text(
            f"Setup complete!\n\n"
            f"Your daily targets:\n"
            f"- Calories: {targets.calories}\n"
            f"- Protein: {targets.protein}g\n"
            f"- Carbs: {targets.carbs}g\n"
            f"- Fat: {targets.fat}g\n\n"
            f"Use /plan to get your first meal plan!\n"
            f"Use /help to see all commands.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        await update.message.reply_text(
            "Setup cancelled. Use /start to begin again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def plan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /plan command - show today's meal plan."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        today = date.today()
        plan = self.db.get_meal_plan(user.id, today)

        if not plan:
            await update.message.reply_text("Generating your meal plan...")

            # Get recent meals to avoid repetition
            recent_plans = self.db.get_recent_meal_plans(user.id, days=7)
            recent_meals = []
            for p in recent_plans:
                if hasattr(p.meals, 'breakfast'):
                    recent_meals.append(p.meals.breakfast.name)
                if hasattr(p.meals, 'lunch'):
                    recent_meals.append(p.meals.lunch.name)
                if hasattr(p.meals, 'dinner'):
                    recent_meals.append(p.meals.dinner.name)

            # Generate plan
            planner = AIPlanner()
            plan_data = await planner.generate_meal_plan(user, recent_meals)

            # Calculate totals
            total_cal = sum(
                plan_data.get(m, {}).get("calories", 0)
                for m in ["breakfast", "lunch", "dinner"]
            )
            total_cal += sum(s.get("calories", 0) for s in plan_data.get("snacks", []))

            total_protein = sum(
                plan_data.get(m, {}).get("protein", 0)
                for m in ["breakfast", "lunch", "dinner"]
            )
            total_protein += sum(s.get("protein", 0) for s in plan_data.get("snacks", []))

            total_carbs = sum(
                plan_data.get(m, {}).get("carbs", 0)
                for m in ["breakfast", "lunch", "dinner"]
            )
            total_carbs += sum(s.get("carbs", 0) for s in plan_data.get("snacks", []))

            total_fat = sum(
                plan_data.get(m, {}).get("fat", 0)
                for m in ["breakfast", "lunch", "dinner"]
            )
            total_fat += sum(s.get("fat", 0) for s in plan_data.get("snacks", []))

            # Save plan
            self.db.create_meal_plan(MealPlanCreate(
                user_id=user.id,
                plan_date=today,
                meals=plan_data,
                shopping_list=plan_data.get("shopping_list", []),
                total_calories=total_cal,
                total_protein=total_protein,
                total_carbs=total_carbs,
                total_fat=total_fat,
            ))

            plan = self.db.get_meal_plan(user.id, today)

        # Format and send plan
        message = self._format_meal_plan(plan)
        await update.message.reply_text(message, parse_mode="HTML")

    def _format_meal_plan(self, plan) -> str:
        """Format meal plan as readable message."""
        meals = plan.meals if isinstance(plan.meals, dict) else plan.meals.model_dump()

        lines = [f"<b>Meal Plan - {plan.plan_date.strftime('%B %d, %Y')}</b>\n"]

        for meal_type in ["breakfast", "lunch", "dinner"]:
            meal = meals.get(meal_type, {})
            if meal:
                name = meal.get("name", "N/A")
                calories = meal.get("calories", 0)
                lines.append(f"\n<b>{meal_type.title()}</b>")
                lines.append(f"{name}")
                lines.append(f"  {calories} cal | P: {meal.get('protein', 0)}g | C: {meal.get('carbs', 0)}g | F: {meal.get('fat', 0)}g")

        snacks = meals.get("snacks", [])
        if snacks:
            lines.append(f"\n<b>Snacks</b>")
            for snack in snacks:
                lines.append(f"- {snack.get('name', 'Snack')} ({snack.get('calories', 0)} cal)")

        lines.append(f"\n<b>Daily Total:</b> {plan.total_calories} cal | P: {plan.total_protein}g | C: {plan.total_carbs}g | F: {plan.total_fat}g")

        return "\n".join(lines)

    async def log_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /log command - log food intake."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        # Parse food description from command
        if context.args:
            food_description = " ".join(context.args)
        else:
            await update.message.reply_text(
                "What did you eat? Use:\n"
                "/log chicken salad with rice\n\n"
                "Or use /quick for common foods."
            )
            return

        # Estimate nutrition using AI
        planner = AIPlanner()
        nutrition = await planner.parse_food_log(food_description)

        # Determine meal type by time
        hour = datetime.now().hour
        if hour < 10:
            meal_type = "breakfast"
        elif hour < 14:
            meal_type = "lunch"
        elif hour < 17:
            meal_type = "snack"
        else:
            meal_type = "dinner"

        # Log to database
        self.db.create_food_log(user.id, FoodLogCreate(
            meal_type=meal_type,
            food_description=food_description,
            calories=nutrition.get("calories", 0),
            protein=nutrition.get("protein", 0),
            carbs=nutrition.get("carbs", 0),
            fat=nutrition.get("fat", 0),
        ))

        # Update logging streak
        self.db.update_streak(user.id, "logging")

        # Get daily totals
        totals = self.db.get_daily_totals(user.id, date.today())

        await update.message.reply_text(
            f"Logged: {food_description}\n"
            f"Estimated: {nutrition.get('calories', 0)} cal | "
            f"P: {nutrition.get('protein', 0)}g | "
            f"C: {nutrition.get('carbs', 0)}g | "
            f"F: {nutrition.get('fat', 0)}g\n\n"
            f"Daily total: {totals['calories']} / {user.target_calories or 2000} cal"
        )

    async def quick_log_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /quick command - quick log common foods."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Eggs (2)", callback_data="qlog_eggs"),
                InlineKeyboardButton("Toast", callback_data="qlog_toast"),
            ],
            [
                InlineKeyboardButton("Chicken", callback_data="qlog_chicken"),
                InlineKeyboardButton("Rice", callback_data="qlog_rice"),
            ],
            [
                InlineKeyboardButton("Salad", callback_data="qlog_salad"),
                InlineKeyboardButton("Sandwich", callback_data="qlog_sandwich"),
            ],
            [
                InlineKeyboardButton("Apple", callback_data="qlog_apple"),
                InlineKeyboardButton("Banana", callback_data="qlog_banana"),
            ],
            [
                InlineKeyboardButton("Yogurt", callback_data="qlog_yogurt"),
                InlineKeyboardButton("Protein Bar", callback_data="qlog_protein_bar"),
            ],
        ])

        await update.message.reply_text(
            "Quick log - tap to add:",
            reply_markup=keyboard
        )

    async def suggest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /suggest command - get meal suggestion."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        # Calculate remaining calories
        totals = self.db.get_daily_totals(user.id, date.today())
        remaining = (user.target_calories or 2000) - totals["calories"]

        # Determine meal type
        hour = datetime.now().hour
        if hour < 10:
            meal_type = "breakfast"
        elif hour < 14:
            meal_type = "lunch"
        elif hour < 17:
            meal_type = "snack"
        else:
            meal_type = "dinner"

        await update.message.reply_text(f"Finding a {meal_type} suggestion...")

        planner = AIPlanner()
        suggestion = await planner.get_meal_suggestion(user, meal_type, remaining)

        await update.message.reply_text(
            f"<b>Suggestion: {suggestion.name}</b>\n\n"
            f"{suggestion.description or ''}\n\n"
            f"Nutrition:\n"
            f"- Calories: {suggestion.calories}\n"
            f"- Protein: {suggestion.protein}g\n"
            f"- Carbs: {suggestion.carbs}g\n"
            f"- Fat: {suggestion.fat}g\n"
            f"- Prep time: ~{suggestion.prep_time_minutes or 15} min\n\n"
            f"Use /log {suggestion.name} to add it to your food diary.",
            parse_mode="HTML"
        )

    async def snack_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /snack command - get healthy snack ideas."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        totals = self.db.get_daily_totals(user.id, date.today())
        remaining = (user.target_calories or 2000) - totals["calories"]

        # Suggest appropriate snack size
        if remaining > 300:
            snack_cal = 200
        elif remaining > 150:
            snack_cal = 100
        else:
            snack_cal = 50

        planner = AIPlanner()
        suggestion = await planner.get_meal_suggestion(user, "snack", snack_cal)

        await update.message.reply_text(
            f"<b>Snack idea: {suggestion.name}</b>\n\n"
            f"{suggestion.calories} cal | P: {suggestion.protein}g | C: {suggestion.carbs}g | F: {suggestion.fat}g\n\n"
            f"Remaining today: {remaining} cal\n\n"
            f"Use /log {suggestion.name} to track it.",
            parse_mode="HTML"
        )

    async def water_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /water command - log water intake."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        # Parse amount
        amount = 250  # Default glass
        if context.args:
            try:
                amount = int(context.args[0])
            except ValueError:
                pass

        self.db.create_water_log(user.id, WaterLogCreate(amount_ml=amount))

        daily_total = self.db.get_daily_water(user.id, date.today())
        target = NutritionCalculator.calculate_water_target(
            user.weight_kg or 70,
            user.activity_level or "moderate"
        )

        await update.message.reply_text(
            f"Logged {amount}ml of water\n\n"
            f"Today: {daily_total}ml / {target}ml ({round(daily_total/target*100)}%)"
        )

    async def weight_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /weight command - log weight."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        if not context.args:
            # Show weight history
            history = self.db.get_weight_history(user.id, days=7)
            if not history:
                await update.message.reply_text(
                    "No weight logs yet.\n\n"
                    "Log your weight: /weight 70.5"
                )
                return

            lines = ["<b>Weight History (Last 7 days)</b>\n"]
            for log in history[:7]:
                lines.append(f"{log.logged_at.strftime('%b %d')}: {log.weight_kg:.1f} kg")

            if len(history) >= 2:
                change = history[0].weight_kg - history[-1].weight_kg
                direction = "down" if change < 0 else "up"
                lines.append(f"\nChange: {abs(change):.1f} kg {direction}")

            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
            return

        try:
            weight = float(context.args[0])
            if weight < 20 or weight > 500:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Please enter a valid weight (20-500 kg)")
            return

        self.db.create_weight_log(user.id, WeightLogCreate(weight_kg=weight))

        # Update user's current weight
        self.db.update_user(user.id, UserUpdate(weight_kg=weight))

        # Check progress
        history = self.db.get_weight_history(user.id, days=7)
        message = f"Logged: {weight} kg"

        if len(history) >= 2:
            change = history[0].weight_kg - history[-1].weight_kg
            if abs(change) > 0.1:
                direction = "lost" if change < 0 else "gained"
                message += f"\n\nThis week: {direction} {abs(change):.1f} kg"

        await update.message.reply_text(message)

    async def progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /progress command - show progress stats."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        # Get weekly report
        report = self.tracker.get_weekly_report(user)
        message = self.tracker.format_weekly_report(report)

        await update.message.reply_text(message)

    async def goals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /goals command - view/update goals."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Change Goal Type", callback_data="goals_change")],
            [InlineKeyboardButton("Update Weight", callback_data="goals_weight")],
            [InlineKeyboardButton("Recalculate Targets", callback_data="goals_recalc")],
        ])

        await update.message.reply_text(
            f"<b>Your Current Goals</b>\n\n"
            f"Goal: {(user.goal_type or 'Not set').replace('_', ' ').title()}\n"
            f"Current weight: {user.weight_kg or 'Not set'} kg\n\n"
            f"<b>Daily Targets:</b>\n"
            f"- Calories: {user.target_calories or 'Not set'}\n"
            f"- Protein: {user.target_protein or 'Not set'}g\n"
            f"- Carbs: {user.target_carbs or 'Not set'}g\n"
            f"- Fat: {user.target_fat or 'Not set'}g",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    async def avoid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /avoid command - show foods to avoid."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        restrictions = user.restrictions or []

        if not restrictions:
            await update.message.reply_text(
                "You haven't set any dietary restrictions.\n\n"
                "Use /settings to add restrictions."
            )
            return

        avoid_foods = {
            "vegetarian": ["meat", "poultry", "fish", "seafood"],
            "vegan": ["meat", "poultry", "fish", "dairy", "eggs", "honey"],
            "gluten-free": ["wheat", "bread", "pasta", "beer", "cereals"],
            "lactose-free": ["milk", "cheese", "yogurt", "cream", "butter"],
            "nut-free": ["peanuts", "almonds", "cashews", "walnuts"],
            "keto": ["sugar", "bread", "pasta", "rice", "potatoes", "fruit juice"],
        }

        lines = ["<b>Foods to Avoid</b>\n"]
        for restriction in restrictions:
            foods = avoid_foods.get(restriction.lower(), [restriction])
            lines.append(f"\n<b>{restriction.title()}:</b>")
            lines.append(", ".join(foods))

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command - adjust settings."""
        user = self._get_user(update)
        if not user:
            return await self._ask_setup(update)

        settings = self.db.get_user_settings(user.id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Change AI Provider", callback_data="settings_ai")],
            [InlineKeyboardButton("Notification Times", callback_data="settings_notif")],
            [InlineKeyboardButton("Dietary Restrictions", callback_data="settings_restrict")],
            [InlineKeyboardButton("Cuisine Preferences", callback_data="settings_cuisine")],
            [InlineKeyboardButton("Toggle Notifications", callback_data="settings_toggle_notif")],
        ])

        await update.message.reply_text(
            f"<b>Settings</b>\n\n"
            f"AI Provider: {settings.ai_provider if settings else 'ollama'}\n"
            f"Morning plan: {settings.morning_plan_time if settings else '07:00'}\n"
            f"Evening summary: {settings.evening_summary_time if settings else '20:00'}\n"
            f"Notifications: {'On' if settings and settings.notifications_enabled else 'Off'}\n\n"
            f"Restrictions: {', '.join(user.restrictions) if user.restrictions else 'None'}\n"
            f"Cuisines: {', '.join(user.cuisine_preferences) if user.cuisine_preferences else 'Any'}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "<b>Diet Agent Commands</b>\n\n"
            "<b>Meal Planning:</b>\n"
            "/plan - Get today's meal plan\n"
            "/suggest - Get a meal suggestion\n"
            "/snack - Get healthy snack ideas\n\n"
            "<b>Logging:</b>\n"
            "/log [food] - Log what you ate\n"
            "/quick - Quick log common foods\n"
            "/water [ml] - Log water (default 250ml)\n"
            "/weight [kg] - Log your weight\n\n"
            "<b>Progress:</b>\n"
            "/progress - Weekly progress report\n"
            "/goals - View/update goals\n\n"
            "<b>Settings:</b>\n"
            "/avoid - Foods to avoid\n"
            "/settings - Adjust preferences\n"
            "/help - Show this help\n\n"
            "Tip: You'll receive automated meal reminders based on your settings!",
            parse_mode="HTML"
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()

        user = self._get_user_from_callback(update)
        if not user:
            return

        data = query.data

        # Quick log callbacks
        if data.startswith("qlog_"):
            food_map = {
                "qlog_eggs": ("2 eggs", {"calories": 156, "protein": 12, "carbs": 2, "fat": 10}),
                "qlog_toast": ("Toast with butter", {"calories": 120, "protein": 3, "carbs": 20, "fat": 4}),
                "qlog_chicken": ("Grilled chicken breast", {"calories": 165, "protein": 31, "carbs": 0, "fat": 4}),
                "qlog_rice": ("Cup of rice", {"calories": 200, "protein": 4, "carbs": 45, "fat": 0}),
                "qlog_salad": ("Mixed salad", {"calories": 50, "protein": 2, "carbs": 10, "fat": 0}),
                "qlog_sandwich": ("Sandwich", {"calories": 350, "protein": 15, "carbs": 40, "fat": 15}),
                "qlog_apple": ("Apple", {"calories": 95, "protein": 0, "carbs": 25, "fat": 0}),
                "qlog_banana": ("Banana", {"calories": 105, "protein": 1, "carbs": 27, "fat": 0}),
                "qlog_yogurt": ("Greek yogurt", {"calories": 100, "protein": 10, "carbs": 6, "fat": 3}),
                "qlog_protein_bar": ("Protein bar", {"calories": 200, "protein": 20, "carbs": 22, "fat": 8}),
            }

            if data in food_map:
                food_name, nutrition = food_map[data]

                # Determine meal type
                hour = datetime.now().hour
                if hour < 10:
                    meal_type = "breakfast"
                elif hour < 14:
                    meal_type = "lunch"
                elif hour < 17:
                    meal_type = "snack"
                else:
                    meal_type = "dinner"

                self.db.create_food_log(user.id, FoodLogCreate(
                    meal_type=meal_type,
                    food_description=food_name,
                    **nutrition
                ))

                self.db.update_streak(user.id, "logging")
                totals = self.db.get_daily_totals(user.id, date.today())

                await query.edit_message_text(
                    f"Logged: {food_name}\n"
                    f"{nutrition['calories']} cal | P: {nutrition['protein']}g\n\n"
                    f"Daily total: {totals['calories']} / {user.target_calories or 2000} cal"
                )

        # Settings callbacks
        elif data == "settings_ai":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ollama (Local)", callback_data="setai_ollama")],
                [InlineKeyboardButton("Groq (Cloud Free)", callback_data="setai_groq")],
                [InlineKeyboardButton("Gemini (Google Free)", callback_data="setai_gemini")],
                [InlineKeyboardButton("Rule-based (No AI)", callback_data="setai_rule_based")],
            ])
            await query.edit_message_text(
                "Select AI provider for meal planning:",
                reply_markup=keyboard
            )

        elif data.startswith("setai_"):
            provider = data.replace("setai_", "")
            self.db.update_user_settings(user.id, {"ai_provider": provider})
            await query.edit_message_text(f"AI provider set to: {provider}")

        elif data == "settings_toggle_notif":
            settings = self.db.get_user_settings(user.id)
            new_state = not settings.notifications_enabled if settings else True
            self.db.update_user_settings(user.id, {"notifications_enabled": new_state})
            await query.edit_message_text(
                f"Notifications {'enabled' if new_state else 'disabled'}"
            )

        elif data == "goals_recalc":
            if user.weight_kg and user.height_cm and user.age:
                targets = NutritionCalculator.calculate_targets(
                    weight_kg=user.weight_kg,
                    height_cm=user.height_cm,
                    age=user.age,
                    gender=user.gender or "other",
                    activity_level=user.activity_level or "moderate",
                    goal_type=user.goal_type or "maintenance",
                )

                self.db.update_user(user.id, UserUpdate(
                    target_calories=targets.calories,
                    target_protein=targets.protein,
                    target_carbs=targets.carbs,
                    target_fat=targets.fat,
                ))

                await query.edit_message_text(
                    f"Targets recalculated!\n\n"
                    f"- Calories: {targets.calories}\n"
                    f"- Protein: {targets.protein}g\n"
                    f"- Carbs: {targets.carbs}g\n"
                    f"- Fat: {targets.fat}g"
                )
            else:
                await query.edit_message_text(
                    "Missing profile data. Please use /start to complete setup."
                )

    def _get_user(self, update: Update):
        """Get user from database by telegram ID."""
        return self.db.get_user_by_telegram_id(update.effective_user.id)

    def _get_user_from_callback(self, update: Update):
        """Get user from callback query."""
        return self.db.get_user_by_telegram_id(update.callback_query.from_user.id)

    async def _ask_setup(self, update: Update) -> None:
        """Ask user to complete setup."""
        await update.message.reply_text(
            "Please complete your profile setup first.\n"
            "Use /start to begin."
        )

    async def send_message(self, telegram_id: int, message: str) -> bool:
        """Send a message to a user (for scheduled notifications)."""
        if not self.app:
            return False

        try:
            await self.app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            print(f"Failed to send message to {telegram_id}: {e}")
            return False

    def run(self) -> None:
        """Run the bot."""
        app = self.create_application()
        print("Diet Agent bot is running...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
