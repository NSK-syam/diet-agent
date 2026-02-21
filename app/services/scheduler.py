"""APScheduler for 24/7 automated notifications."""

import asyncio
from datetime import datetime, date, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db.supabase import DatabaseService
from app.models.meal import MealPlanCreate
from app.services.ai_planner import AIPlanner
from app.services.goal_tracker import GoalTracker


class NotificationScheduler:
    """Scheduled notifications for Diet Agent."""

    def __init__(self, telegram_bot):
        self.settings = get_settings()
        self.db = DatabaseService()
        self.tracker = GoalTracker()
        self.bot = telegram_bot
        self.scheduler = AsyncIOScheduler(timezone=self.settings.timezone)
        self.planner = AIPlanner()

    def start(self) -> None:
        """Start the scheduler with default jobs."""
        # Parse default times
        morning_hour, morning_min = map(int, self.settings.morning_plan_time.split(":"))
        evening_hour, evening_min = map(int, self.settings.evening_summary_time.split(":"))

        # Morning meal plan
        self.scheduler.add_job(
            self._send_morning_plans,
            CronTrigger(hour=morning_hour, minute=morning_min),
            id="morning_plans",
            replace_existing=True,
        )

        # Evening summary
        self.scheduler.add_job(
            self._send_evening_summaries,
            CronTrigger(hour=evening_hour, minute=evening_min),
            id="evening_summaries",
            replace_existing=True,
        )

        # Weekly report (Sunday 9 AM)
        self.scheduler.add_job(
            self._send_weekly_reports,
            CronTrigger(day_of_week="sun", hour=9, minute=0),
            id="weekly_reports",
            replace_existing=True,
        )

        # Meal reminders (breakfast, lunch, dinner)
        self.scheduler.add_job(
            self._send_meal_reminders,
            CronTrigger(hour=8, minute=0),
            id="breakfast_reminder",
            kwargs={"meal_type": "breakfast"},
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._send_meal_reminders,
            CronTrigger(hour=12, minute=0),
            id="lunch_reminder",
            kwargs={"meal_type": "lunch"},
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._send_meal_reminders,
            CronTrigger(hour=18, minute=0),
            id="dinner_reminder",
            kwargs={"meal_type": "dinner"},
            replace_existing=True,
        )

        # Water reminders (every 2 hours from 8 AM to 8 PM)
        if self.settings.enable_water_reminders:
            self.scheduler.add_job(
                self._send_water_reminders,
                CronTrigger(hour="8-20/2", minute=30),
                id="water_reminders",
                replace_existing=True,
            )

        self.scheduler.start()
        print("Notification scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("Notification scheduler stopped")

    async def _send_morning_plans(self) -> None:
        """Send morning meal plans to all users."""
        print(f"[{datetime.now()}] Sending morning meal plans...")

        users = self.db.get_all_users_with_notifications()

        for user in users:
            try:
                # Check if user has a plan for today
                today = date.today()
                existing_plan = self.db.get_meal_plan(user.id, today)

                if not existing_plan:
                    # Generate new plan
                    recent_plans = self.db.get_recent_meal_plans(user.id, days=7)
                    recent_meals = []
                    for p in recent_plans:
                        meals = p.meals if isinstance(p.meals, dict) else {}
                        for meal_type in ["breakfast", "lunch", "dinner"]:
                            if meal_type in meals:
                                recent_meals.append(meals[meal_type].get("name", ""))

                    plan_data = await self.planner.generate_meal_plan(user, recent_meals)

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

                    total_carbs = sum(
                        plan_data.get(m, {}).get("carbs", 0)
                        for m in ["breakfast", "lunch", "dinner"]
                    )

                    total_fat = sum(
                        plan_data.get(m, {}).get("fat", 0)
                        for m in ["breakfast", "lunch", "dinner"]
                    )

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

                    existing_plan = self.db.get_meal_plan(user.id, today)

                # Format and send plan
                message = self._format_morning_plan(existing_plan, user.name)
                await self.bot.send_message(user.telegram_id, message)

            except Exception as e:
                print(f"Error sending morning plan to {user.telegram_id}: {e}")

    def _format_morning_plan(self, plan, name: Optional[str]) -> str:
        """Format morning meal plan message."""
        greeting = f"Good morning{', ' + name if name else ''}!"
        meals = plan.meals if isinstance(plan.meals, dict) else {}

        lines = [
            f"<b>{greeting}</b>\n",
            "Here's your meal plan for today:\n",
        ]

        for meal_type in ["breakfast", "lunch", "dinner"]:
            meal = meals.get(meal_type, {})
            if meal:
                lines.append(f"<b>{meal_type.title()}</b>: {meal.get('name', 'N/A')}")
                lines.append(f"   {meal.get('calories', 0)} cal\n")

        lines.append(f"\n<b>Total:</b> {plan.total_calories} cal")
        lines.append("\nUse /plan for full details!")

        return "\n".join(lines)

    async def _send_evening_summaries(self) -> None:
        """Send evening summaries to all users."""
        print(f"[{datetime.now()}] Sending evening summaries...")

        users = self.db.get_all_users_with_notifications()

        for user in users:
            try:
                progress = self.tracker.get_daily_progress(user, date.today())
                message = self._format_evening_summary(progress, user.name)
                await self.bot.send_message(user.telegram_id, message)
            except Exception as e:
                print(f"Error sending evening summary to {user.telegram_id}: {e}")

    def _format_evening_summary(self, progress, name: Optional[str]) -> str:
        """Format evening summary message."""
        greeting = f"Good evening{', ' + name if name else ''}!"

        cal_pct = round(progress.calories_consumed / progress.calories_target * 100) if progress.calories_target else 0

        if progress.on_track:
            status = "Great job staying on track today!"
        elif progress.meals_logged == 0:
            status = "Don't forget to log your meals!"
        elif cal_pct < 80:
            status = "You're under your calorie target. Consider having a healthy snack!"
        else:
            status = "You're slightly over target. Try to balance tomorrow!"

        return f"""<b>{greeting}</b>

<b>Today's Summary:</b>
Calories: {progress.calories_consumed} / {progress.calories_target} ({cal_pct}%)
Protein: {progress.protein_consumed}g / {progress.protein_target}g
Meals logged: {progress.meals_logged}
Water: {progress.water_ml}ml

{status}

Use /log to add anything you missed!"""

    async def _send_weekly_reports(self) -> None:
        """Send weekly reports to all users."""
        print(f"[{datetime.now()}] Sending weekly reports...")

        users = self.db.get_all_users_with_notifications()

        for user in users:
            try:
                report = self.tracker.get_weekly_report(user)
                message = self.tracker.format_weekly_report(report)
                await self.bot.send_message(user.telegram_id, f"<b>Your Weekly Report</b>\n\n{message}")
            except Exception as e:
                print(f"Error sending weekly report to {user.telegram_id}: {e}")

    async def _send_meal_reminders(self, meal_type: str) -> None:
        """Send meal reminders."""
        print(f"[{datetime.now()}] Sending {meal_type} reminders...")

        users = self.db.get_all_users_with_notifications()

        for user in users:
            try:
                # Check if they have a plan for today
                plan = self.db.get_meal_plan(user.id, date.today())

                if plan:
                    meals = plan.meals if isinstance(plan.meals, dict) else {}
                    meal = meals.get(meal_type, {})

                    if meal:
                        message = f"Time for {meal_type}!\n\n<b>{meal.get('name', 'Your planned meal')}</b>\n{meal.get('calories', 0)} cal\n\nUse /log to track when you're done!"
                        await self.bot.send_message(user.telegram_id, message)
            except Exception as e:
                print(f"Error sending {meal_type} reminder to {user.telegram_id}: {e}")

    async def _send_water_reminders(self) -> None:
        """Send water intake reminders."""
        print(f"[{datetime.now()}] Sending water reminders...")

        users = self.db.get_all_users_with_notifications()

        for user in users:
            try:
                settings = self.db.get_user_settings(user.id)
                if settings and settings.enable_water_reminders:
                    daily_water = self.db.get_daily_water(user.id, date.today())
                    target = 2500  # Default target

                    if daily_water < target:
                        remaining = target - daily_water
                        glasses = remaining // 250

                        message = f"Stay hydrated!\n\nToday: {daily_water}ml / {target}ml\n\nTry to drink {glasses} more glasses today.\n\nUse /water to log!"
                        await self.bot.send_message(user.telegram_id, message)
            except Exception as e:
                print(f"Error sending water reminder to {user.telegram_id}: {e}")
