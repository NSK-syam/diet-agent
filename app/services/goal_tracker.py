"""Goal tracking and progress reporting."""

from datetime import date, datetime, timedelta
from typing import Optional, List
from uuid import UUID

from app.db.supabase import DatabaseService
from app.models.user import User
from app.models.tracking import DailyProgress, WeeklyReport


class GoalTracker:
    """Track progress towards diet goals."""

    def __init__(self):
        self.db = DatabaseService()

    def get_daily_progress(self, user: User, target_date: Optional[date] = None) -> DailyProgress:
        """Get progress for a specific day."""
        target_date = target_date or date.today()

        # Get daily totals
        totals = self.db.get_daily_totals(user.id, target_date)
        water = self.db.get_daily_water(user.id, target_date)

        # Calculate targets
        cal_target = user.target_calories or 2000
        protein_target = user.target_protein or 150
        carbs_target = user.target_carbs or 250
        fat_target = user.target_fat or 65

        # Check if on track (within 15% of targets)
        cal_diff = abs(totals["calories"] - cal_target) / cal_target if cal_target else 0
        on_track = cal_diff <= 0.15 and totals["meals_logged"] >= 2

        return DailyProgress(
            date=datetime.combine(target_date, datetime.min.time()),
            calories_consumed=totals["calories"],
            calories_target=cal_target,
            protein_consumed=totals["protein"],
            protein_target=protein_target,
            carbs_consumed=totals["carbs"],
            carbs_target=carbs_target,
            fat_consumed=totals["fat"],
            fat_target=fat_target,
            water_ml=water,
            meals_logged=totals["meals_logged"],
            on_track=on_track,
        )

    def get_weekly_report(self, user: User, end_date: Optional[date] = None) -> WeeklyReport:
        """Generate weekly progress report."""
        end_date = end_date or date.today()
        start_date = end_date - timedelta(days=6)

        # Collect daily data
        daily_data = []
        days_on_track = 0

        for i in range(7):
            day = start_date + timedelta(days=i)
            progress = self.get_daily_progress(user, day)
            daily_data.append(progress)
            if progress.on_track:
                days_on_track += 1

        # Calculate averages
        total_days = len(daily_data)
        avg_calories = sum(d.calories_consumed for d in daily_data) / total_days
        avg_protein = sum(d.protein_consumed for d in daily_data) / total_days
        avg_carbs = sum(d.carbs_consumed for d in daily_data) / total_days
        avg_fat = sum(d.fat_consumed for d in daily_data) / total_days

        # Get weight change
        weight_history = self.db.get_weight_history(user.id, days=7)
        weight_change = None
        if len(weight_history) >= 2:
            weight_change = weight_history[0].weight_kg - weight_history[-1].weight_kg

        # Get logging streak
        streak = self.db.get_streak(user.id, "logging")
        logging_streak = streak.current_streak if streak else 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            user, daily_data, avg_calories, avg_protein, weight_change
        )

        return WeeklyReport(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()),
            avg_calories=round(avg_calories),
            avg_protein=round(avg_protein),
            avg_carbs=round(avg_carbs),
            avg_fat=round(avg_fat),
            weight_change=weight_change,
            days_on_track=days_on_track,
            total_days=total_days,
            logging_streak=logging_streak,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        user: User,
        daily_data: List[DailyProgress],
        avg_calories: float,
        avg_protein: float,
        weight_change: Optional[float],
    ) -> List[str]:
        """Generate personalized recommendations based on progress."""
        recommendations = []

        cal_target = user.target_calories or 2000
        protein_target = user.target_protein or 150

        # Calorie analysis
        cal_diff_pct = (avg_calories - cal_target) / cal_target * 100

        if user.goal_type == "weight_loss":
            if cal_diff_pct > 10:
                recommendations.append(
                    "You're averaging above your calorie target. Try portion control or swap high-calorie snacks."
                )
            elif cal_diff_pct < -20:
                recommendations.append(
                    "You're eating too little. Severe restriction can slow metabolism. Aim closer to your target."
                )
            elif weight_change and weight_change < -0.5:
                recommendations.append(
                    "Great progress this week! You're losing weight at a healthy rate."
                )

        elif user.goal_type == "muscle_gain":
            if cal_diff_pct < -5:
                recommendations.append(
                    "You need to eat more to build muscle. Add calorie-dense healthy foods."
                )
            if avg_protein < protein_target * 0.9:
                recommendations.append(
                    "Increase protein intake for muscle growth. Add eggs, chicken, or protein shakes."
                )

        # Protein check
        if avg_protein < protein_target * 0.8:
            recommendations.append(
                f"Your protein intake is low (avg {round(avg_protein)}g vs target {protein_target}g). "
                "Add lean meats, eggs, legumes, or Greek yogurt."
            )

        # Consistency check
        logged_days = sum(1 for d in daily_data if d.meals_logged > 0)
        if logged_days < 5:
            recommendations.append(
                "Try to log your meals more consistently. Tracking helps you stay aware of your intake."
            )

        # Water reminder
        avg_water = sum(d.water_ml for d in daily_data) / len(daily_data)
        if avg_water < 1500:
            recommendations.append(
                "Your water intake seems low. Aim for at least 2-3 liters daily."
            )

        # Add positive reinforcement
        on_track_days = sum(1 for d in daily_data if d.on_track)
        if on_track_days >= 5:
            recommendations.insert(0, "Excellent consistency this week! Keep up the great work!")
        elif on_track_days >= 3:
            recommendations.insert(0, "Good progress! You're building healthy habits.")

        return recommendations[:5]  # Limit to 5 recommendations

    def format_daily_summary(self, progress: DailyProgress) -> str:
        """Format daily progress as a readable message."""
        cal_pct = round(progress.calories_consumed / progress.calories_target * 100) if progress.calories_target else 0
        protein_pct = round(progress.protein_consumed / progress.protein_target * 100) if progress.protein_target else 0

        status = "On track!" if progress.on_track else "Keep going!"

        return f"""Daily Summary - {progress.date.strftime('%B %d')}

Calories: {progress.calories_consumed} / {progress.calories_target} ({cal_pct}%)
Protein: {progress.protein_consumed}g / {progress.protein_target}g ({protein_pct}%)
Carbs: {progress.carbs_consumed}g / {progress.carbs_target}g
Fat: {progress.fat_consumed}g / {progress.fat_target}g
Water: {progress.water_ml}ml
Meals logged: {progress.meals_logged}

Status: {status}"""

    def format_weekly_report(self, report: WeeklyReport) -> str:
        """Format weekly report as a readable message."""
        weight_str = ""
        if report.weight_change is not None:
            direction = "lost" if report.weight_change < 0 else "gained"
            weight_str = f"\nWeight: {direction} {abs(report.weight_change):.1f}kg"

        recs = "\n".join(f"- {r}" for r in report.recommendations)

        return f"""Weekly Report
{report.start_date.strftime('%b %d')} - {report.end_date.strftime('%b %d')}

Average Daily Intake:
- Calories: {round(report.avg_calories)}
- Protein: {round(report.avg_protein)}g
- Carbs: {round(report.avg_carbs)}g
- Fat: {round(report.avg_fat)}g
{weight_str}
Days on track: {report.days_on_track} / {report.total_days}
Logging streak: {report.logging_streak} days

Recommendations:
{recs}"""
