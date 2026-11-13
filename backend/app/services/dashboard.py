import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import DashboardSummary
from app.schemas.goals import GoalResponse
from app.schemas.planner import StudySessionResponse

logger = logging.getLogger("studyflow.services.dashboard")


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    async def summary(self, time_zone: str = "UTC") -> DashboardSummary:
        logger.debug("dashboard_summary_requested")
        counts = await self.repository.summary_counts()
        planner = int(counts["planner"])
        completed_planner = int(counts["completed_planner"])
        goals = int(counts["goals"])
        completed_goals = int(counts["completed_goals"])
        now = datetime.now(ZoneInfo(time_zone))
        today = await self.repository.today_data(now.date(), now.strftime("%H:%M"))
        result = DashboardSummary(
            date=now.date(),
            timeZone=time_zone,
            todaySessions=[StudySessionResponse.model_validate(item) for item in today["sessions"]],
            nextSession=StudySessionResponse.model_validate(today["next_session"])
            if today["next_session"]
            else None,
            upcomingGoals=[GoalResponse.model_validate(item) for item in today["goals"]],
            todaySessionCount=today["counts"]["total"],
            todayCompletedCount=today["counts"]["completed"],
            todayPlannedMinutes=today["counts"]["minutes"],
            undatedPlannerCount=today["counts"]["undated"],
            overdueGoalCount=today["overdue"],
            plannerCount=planner,
            completedPlanner=completed_planner,
            pendingPlanner=planner - completed_planner,
            plannerCompletionRate=(completed_planner * 100 + planner // 2) // planner
            if planner
            else 0,
            totalGoals=goals,
            completedGoals=completed_goals,
            pendingGoals=goals - completed_goals,
            completionRate=(completed_goals * 100 + goals // 2) // goals if goals else 0,
            totalNotes=int(counts["notes"]),
            totalSessions=int(counts["sessions"]),
            activeGoalTitle=str(counts["active_goal"]),
        )

        return result
