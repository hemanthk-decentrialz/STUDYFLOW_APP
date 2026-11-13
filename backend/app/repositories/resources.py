import logging
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import ColumnElement, case, func, or_, select, update

from app.core.exceptions import ApiError
from app.core.types import FilterValue
from app.models.course import Course
from app.models.goal import Goal
from app.models.note import Note
from app.models.study_session import StudySession
from app.models.timer import Timer
from app.repositories.owned import OwnedRepository

Resource = Note | Goal | StudySession | Course

logger = logging.getLogger("studyflow.repositories.resources")


class ResourceRepository[ModelT: Resource](OwnedRepository):
    model: type[ModelT]
    search_fields: ClassVar[tuple[str, ...]]
    duplicate_fields: ClassVar[tuple[str, ...]]
    sort_fields: ClassVar[tuple[str, ...]]

    def active_conditions(self) -> list[ColumnElement[bool]]:
        return [self.model.user_id == self.user_id, self.model.deleted_at.is_(None)]

    async def get(self, resource_id: int) -> ModelT | None:
        return await self.session.scalar(
            select(self.model).where(*self.active_conditions(), self.model.id == resource_id)
        )

    async def get_including_deleted(self, resource_id: int) -> ModelT | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.user_id == self.user_id, self.model.id == resource_id
            )
        )

    async def restore(self, record: ModelT) -> ModelT:
        record.deleted_at = None
        if isinstance(record, Note):
            record.version += 1
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def id_exists(self, resource_id: int) -> bool:
        # Deleted IDs remain reserved; POST never silently restores a deleted record.
        return (
            await self.session.scalar(
                select(self.model.id).where(
                    self.model.user_id == self.user_id, self.model.id == resource_id
                )
            )
            is not None
        )

    async def duplicate_exists(
        self, values: dict[str, object], exclude_id: int | None = None
    ) -> bool:
        conditions = self.active_conditions()
        for name in self.duplicate_fields:
            column = getattr(self.model, name)
            if name == "scheduled_date":
                conditions.append(
                    column.is_(None) if values[name] is None else column == values[name]
                )
            else:
                conditions.append(
                    func.lower(func.btrim(column)) == func.lower(func.btrim(values[name]))
                )
        if exclude_id is not None:
            conditions.append(self.model.id != exclude_id)
        return (
            await self.session.scalar(select(self.model.id).where(*conditions).limit(1)) is not None
        )

    async def active_goal(self, goal_id: int) -> Goal | None:
        return await self.session.scalar(
            select(Goal).where(
                Goal.id == goal_id, Goal.user_id == self.user_id, Goal.deleted_at.is_(None)
            )
        )

    async def course_has_resources(self, course_id: int) -> bool:
        if (
            await self.session.scalar(
                select(Timer.user_id).where(
                    Timer.user_id == self.user_id,
                    Timer.course_id == course_id,
                    Timer.is_running.is_(True),
                )
            )
            is not None
        ):
            return True
        for model in (StudySession, Note, Goal):
            if (
                await self.session.scalar(
                    select(model.id)
                    .where(
                        model.user_id == self.user_id,
                        model.course_id == course_id,
                        model.deleted_at.is_(None),
                    )
                    .limit(1)
                )
                is not None
            ):
                return True
        return False

    async def clear_timer_course(self, course_id: int) -> None:
        await self.session.execute(
            update(Timer)
            .where(
                Timer.user_id == self.user_id,
                Timer.course_id == course_id,
                Timer.is_running.is_(False),
            )
            .values(course_id=None, revision=Timer.revision + 1)
        )

    async def sync_course_label(self, course_id: int, title: str) -> None:
        for model in (StudySession, Note, Goal):
            await self.session.execute(
                update(model)
                .where(model.user_id == self.user_id, model.course_id == course_id)
                .values(
                    **(
                        {"subject": title, "version": Note.version + 1}
                        if model is Note
                        else {"subject": title}
                    )
                )
            )

    async def unlink_goal(self, goal_id: int) -> None:
        await self.session.execute(
            update(StudySession)
            .where(StudySession.user_id == self.user_id, StudySession.goal_id == goal_id)
            .values(goal_id=None)
        )

    async def create(self, values: dict[str, object]) -> ModelT:
        logger.debug("resource_insert_started")
        position = await self.session.scalar(
            select(func.coalesce(func.max(self.model.position), -1) + 1).where(
                *self.active_conditions()
            )
        )
        record = self.model(user_id=self.user_id, position=position, **values)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: ModelT, changes: dict[str, object]) -> ModelT:
        logger.debug("resource_update_started")
        for name, value in changes.items():
            setattr(record, name, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def soft_delete(self, record: ModelT) -> None:
        logger.debug("resource_soft_delete_started")
        record.deleted_at = datetime.now(UTC)
        if isinstance(record, Note):
            record.version += 1
        await self.session.flush()

    async def list_page(
        self,
        *,
        page: int,
        limit: int,
        search: str | None,
        sort_by: str,
        order: str,
        filters: dict[str, FilterValue],
    ) -> tuple[list[ModelT], int]:
        logger.debug("resource_page_query_started")
        conditions = self.active_conditions()
        if search:
            pattern = (
                "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            )
            conditions.append(
                or_(
                    *[
                        getattr(self.model, name).ilike(pattern, escape="\\")
                        for name in self.search_fields
                    ]
                )
            )
        for name, value in filters.items():
            if name in {"title", "subject"}:
                conditions.append(
                    func.lower(func.btrim(getattr(self.model, name)))
                    == func.lower(func.btrim(value))
                )
            elif name == "goal_id" and self.model is Goal:
                conditions.append(Goal.id == value)
            elif name == "completed" and self.model is Goal:
                conditions.append(Goal.progress == 100 if value else Goal.progress < 100)
            elif name in {"date_from", "date_to"} and self.model is StudySession:
                conditions.append(
                    StudySession.scheduled_date >= value
                    if name == "date_from"
                    else StudySession.scheduled_date <= value
                )
            elif name in {"progress_min", "progress_max", "deadline_from", "deadline_to"}:
                field = "progress" if name.startswith("progress") else "deadline"
                column = getattr(self.model, field)
                conditions.append(
                    column >= value if name.endswith(("min", "from")) else column <= value
                )
            else:
                conditions.append(getattr(self.model, name) == value)
        if sort_by not in self.sort_fields or order not in {"asc", "desc"}:
            raise ApiError(422, "Unsupported sorting option.")
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(self.model).where(*conditions)
            )
            or 0
        )
        column = getattr(self.model, sort_by)
        if self.model is StudySession and sort_by == "priority":
            column = case(
                (StudySession.priority == "Low", 0), (StudySession.priority == "Medium", 1), else_=2
            )
        statement = (
            select(self.model)
            .where(*conditions)
            .order_by(column.desc() if order == "desc" else column.asc(), self.model.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        records = await self.session.scalars(statement)
        return list(records.all()), total


class PlannerRepository(ResourceRepository[StudySession]):
    model = StudySession
    search_fields = ("subject",)
    duplicate_fields = ("subject", "time", "scheduled_date")
    sort_fields = (
        "position",
        "id",
        "subject",
        "time",
        "scheduled_date",
        "priority",
        "completed",
        "duration_minutes",
        "created_at",
        "updated_at",
    )


class NoteRepository(ResourceRepository[Note]):
    model = Note
    search_fields = ("title", "subject", "content")
    duplicate_fields = ("title",)
    sort_fields = ("position", "id", "title", "subject", "created_at", "updated_at")


class GoalRepository(ResourceRepository[Goal]):
    model = Goal
    search_fields = ("title", "subject")
    duplicate_fields = ("title",)
    sort_fields = (
        "position",
        "id",
        "title",
        "subject",
        "deadline",
        "progress",
        "created_at",
        "updated_at",
    )


class CourseRepository(ResourceRepository[Course]):
    model = Course
    search_fields = ("title", "description")
    duplicate_fields = ("title",)
    sort_fields = ("position", "id", "title", "created_at", "updated_at")
