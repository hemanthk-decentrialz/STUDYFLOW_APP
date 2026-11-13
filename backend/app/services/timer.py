import logging
import math
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.exceptions import ApiError
from app.models.timer import Timer
from app.repositories.timer import TimerRepository
from app.schemas.resources import Page
from app.schemas.timer import (
    FocusCourse,
    FocusDay,
    FocusListParams,
    FocusResponse,
    FocusSummary,
    TimerPatchRequest,
    TimerState,
)
from app.services.settings import SettingsService

logger = logging.getLogger("studyflow.services.timer")


class TimerService:
    def __init__(self, repository: TimerRepository, preferences: SettingsService) -> None:
        self.repository = repository
        self.preferences = preferences

    async def end_interval(self, state: TimerState, now: datetime, outcome: str) -> None:
        if state.active_focus_id:
            record = await self.repository.focus(state.active_focus_id)
            if record is not None and record.ended_at is None:
                record.ended_at = max(record.started_at, min(now, record.planned_end_at))
                record.outcome = outcome
        state.active_focus_id = None

    async def expire(self, state: TimerState, now: datetime) -> bool:
        if not state.is_running or not state.end_at or state.end_at > int(now.timestamp() * 1000):
            return False
        ended = datetime.fromtimestamp(state.end_at / 1000, UTC)
        await self.end_interval(state, ended, "completed")
        state.is_running = False
        state.time_left = 0
        state.last_completed_at = state.end_at
        state.last_completed_mode = state.mode
        state.completed_sessions += int(state.mode == "Pomodoro")
        state.end_at = None
        state.revision += 1
        return True

    async def persist(self, state: TimerState) -> TimerState:
        record = await self.repository.save(
            Timer(user_id=self.repository.user_id, **state.model_dump())
        )
        return TimerState.model_validate(record)

    async def get_timer(self) -> TimerState:
        await self.repository.lock_owner()
        record = await self.repository.get()
        durations = (await self.preferences.get_settings()).durations
        state = (
            TimerState.model_validate(record)
            if record
            else TimerState(timeLeft=durations["Pomodoro"], blockDuration=durations["Pomodoro"])
        )
        now = datetime.now(UTC)
        if await self.expire(state, now):
            state = await self.persist(state)
        if (
            not state.is_running
            and state.time_left == state.block_duration
            and state.block_duration != durations[state.mode]
        ):
            state.time_left = durations[state.mode]
            state.block_duration = durations[state.mode]
            state.revision += 1
            state = await self.persist(state)
        if state.is_running and state.end_at:
            state.time_left = max(0, math.ceil((state.end_at - int(now.timestamp() * 1000)) / 1000))
        return state

    async def patch_timer(self, payload: TimerPatchRequest) -> TimerState:
        await self.repository.lock_owner()
        record = await self.repository.get()
        durations = (await self.preferences.get_settings()).durations
        state = (
            TimerState.model_validate(record)
            if record
            else TimerState(timeLeft=durations["Pomodoro"], blockDuration=durations["Pomodoro"])
        )
        if payload.expected_revision != state.revision:
            raise ApiError(409, "The timer changed in another tab. Reload its current state.")
        now = datetime.now(UTC)
        await self.expire(state, now)
        changes = payload.timer.model_dump(exclude_unset=True)
        mode = changes.get("mode", state.mode)
        running = changes.get("is_running", state.is_running)
        course_id = changes.get("course_id", state.course_id)
        if course_id is not None and await self.repository.active_course(course_id) is None:
            raise ApiError(404, "Course not found.")
        if state.is_running and course_id != state.course_id:
            raise ApiError(409, "Pause the timer before changing its course.")
        mode_changed = mode != state.mode
        resetting = not running and changes.get("time_left") == durations[mode]
        if mode_changed or resetting:
            await self.end_interval(state, now, "cancelled")
            state.is_running = False
            state.end_at = None
            state.time_left = durations[mode]
            state.block_duration = durations[mode]
        elif state.is_running and not running:
            await self.end_interval(state, now, "paused")
            state.time_left = max(
                0, math.ceil(((state.end_at or 0) - int(now.timestamp() * 1000)) / 1000)
            )
            state.is_running = False
            state.end_at = None
        state.mode = mode
        state.course_id = course_id
        if running and not state.is_running:
            # New blocks use their mode duration; paused blocks resume the server remainder.
            remaining = (
                state.time_left if 0 < state.time_left < state.block_duration else durations[mode]
            )
            if not (0 < state.time_left < state.block_duration):
                state.block_duration = durations[mode]
            state.time_left = min(7200, remaining)
            end = now + timedelta(seconds=state.time_left)
            state.end_at = int(end.timestamp() * 1000)
            state.is_running = True
            if mode == "Pomodoro":
                focus = await self.repository.start_focus(course_id, now, end)
                state.active_focus_id = focus.id
        state.revision += 1
        logger.info("timer_transition mode=%s running=%s", state.mode, state.is_running)
        return await self.persist(state)

    async def focus_page(self, params: FocusListParams) -> Page[FocusResponse]:
        await self.get_timer()
        records, total = await self.repository.focus_page(
            params.page, params.limit, params.order, params.course_id
        )
        return Page(
            items=[
                FocusResponse(
                    id=record.id,
                    courseId=record.course_id,
                    courseTitle=title,
                    startedAt=record.started_at,
                    endedAt=record.ended_at,
                    seconds=int(seconds),
                    outcome=record.outcome,
                )
                for record, title, seconds in records
            ],
            page=params.page,
            limit=params.limit,
            total=total,
            total_pages=(total + params.limit - 1) // params.limit,
        )

    async def focus_summary(self, time_zone: str) -> FocusSummary:
        await self.get_timer()
        zone = ZoneInfo(time_zone)
        today = datetime.now(zone).date()
        preferences = await self.preferences.get_settings()
        first_weekday = 0 if preferences.weekStartsOn == "monday" else 6
        monday = today - timedelta(days=(today.weekday() - first_weekday) % 7)
        boundaries = [
            datetime.combine(monday + timedelta(days=i), time.min, zone).astimezone(UTC)
            for i in range(8)
        ]
        days, courses, completed = await self.repository.focus_totals(boundaries)
        day_rows = [
            FocusDay(date=monday + timedelta(days=i), seconds=int(seconds))
            for i, seconds in enumerate(days)
        ]
        return FocusSummary(
            weekStart=monday,
            timeZone=time_zone,
            seconds=sum(day.seconds for day in day_rows),
            completedPomodoros=completed,
            days=day_rows,
            courses=[
                FocusCourse(courseId=course_id, title=title, seconds=int(seconds))
                for course_id, title, seconds in courses
            ],
        )
