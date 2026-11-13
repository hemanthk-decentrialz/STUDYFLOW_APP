import logging

from pydantic import BaseModel

from app.core.exceptions import ApiError
from app.models.course import Course
from app.models.goal import Goal
from app.models.note import Note
from app.models.study_session import StudySession
from app.repositories.resources import (
    CourseRepository,
    GoalRepository,
    NoteRepository,
    PlannerRepository,
    Resource,
    ResourceRepository,
)
from app.schemas.courses import CourseResponse
from app.schemas.goals import GoalResponse
from app.schemas.notes import NotePatch, NoteResponse
from app.schemas.planner import StudySessionResponse
from app.schemas.resources import Page, ResourceListParams

logger = logging.getLogger("studyflow.resources")


class ResourceService[ModelT: Resource, ResponseT: BaseModel]:
    def __init__(
        self, repository: ResourceRepository[ModelT], response_schema: type[ResponseT]
    ) -> None:
        self.repository = repository
        self.response_schema = response_schema

    async def list_resources(self, params: ResourceListParams) -> Page[ResponseT]:
        records, total = await self.repository.list_page(
            page=params.page,
            limit=params.limit,
            search=params.search,
            sort_by=params.sort_by,
            order=params.order,
            filters=params.filters(),
        )
        return Page[self.response_schema](
            items=[self.response_schema.model_validate(record) for record in records],
            page=params.page,
            limit=params.limit,
            total=total,
            total_pages=(total + params.limit - 1) // params.limit,
        )

    async def require_resource(self, resource_id: int) -> ModelT:
        record = await self.repository.get(resource_id)
        if record is None:
            # Identical response for deleted, missing, and another user's records.
            raise ApiError(404, "Resource not found.")
        return record

    async def validate_links(self, values: dict[str, object], record: ModelT | None = None) -> None:
        if self.repository.model is Course:
            return
        course_id = values.get("course_id", getattr(record, "course_id", None))
        if not isinstance(course_id, int):
            raise ApiError(422, "Choose a course.")
        course = await self.repository.active_course(course_id)
        if course is None:
            raise ApiError(404, "Course not found.")
        # IDs are authoritative; subject remains a compatibility label for existing clients.
        values["subject"] = course.title
        if self.repository.model is StudySession:
            goal_id = values.get("goal_id", getattr(record, "goal_id", None))
            if goal_id is not None:
                goal = await self.repository.active_goal(int(goal_id))
                if goal is None:
                    raise ApiError(404, "Goal not found.")
                if goal.course_id != course_id:
                    raise ApiError(422, "The linked goal must belong to the selected course.")

    async def create_resource(self, payload: BaseModel) -> ResponseT:
        await self.repository.lock_owner()
        values = payload.model_dump()
        await self.validate_links(values)
        if await self.repository.id_exists(values["id"]):
            raise ApiError(409, "This resource ID has already been used.")
        if await self.repository.duplicate_exists(values):
            raise ApiError(409, "An active resource with this title or study slot already exists.")
        record = await self.repository.create(values)
        logger.info("resource_created kind=%s id=%s", record.__tablename__, record.id)
        return self.response_schema.model_validate(record)

    async def restore_resource(self, resource_id: int) -> ResponseT:
        await self.repository.lock_owner()
        record = await self.repository.get_including_deleted(resource_id)
        if record is None:
            raise ApiError(404, "Resource not found.")
        if record.deleted_at is None:
            return self.response_schema.model_validate(record)
        values = {name: getattr(record, name) for name in self.repository.duplicate_fields}
        await self.validate_links({}, record)
        if await self.repository.duplicate_exists(values, exclude_id=resource_id):
            raise ApiError(
                409, "A matching active resource exists. Rename or remove it before restoring."
            )
        record = await self.repository.restore(record)
        return self.response_schema.model_validate(record)

    async def delete_resource(self, resource_id: int) -> None:
        await self.repository.lock_owner()
        record = await self.require_resource(resource_id)
        if isinstance(record, Course) and await self.repository.course_has_resources(record.id):
            raise ApiError(
                409,
                "This course contains study resources or a running timer. "
                "Remove those or stop the timer first.",
            )
        if isinstance(record, Course):
            await self.repository.clear_timer_course(record.id)
        if isinstance(record, Goal):
            await self.repository.unlink_goal(record.id)
        await self.repository.soft_delete(record)
        logger.info("resource_soft_deleted kind=%s id=%s", record.__tablename__, record.id)


class MutableResourceService[ModelT: Resource, ResponseT: BaseModel](
    ResourceService[ModelT, ResponseT]
):
    async def patch_resource(self, resource_id: int, payload: BaseModel) -> ResponseT:
        await self.repository.lock_owner()
        record = await self.require_resource(resource_id)
        changes = payload.model_dump(exclude_unset=True)
        await self.validate_links(changes, record)
        duplicate_values = {
            name: changes.get(name, getattr(record, name))
            for name in self.repository.duplicate_fields
        }
        if await self.repository.duplicate_exists(duplicate_values, exclude_id=resource_id):
            raise ApiError(409, "An active resource with this title or study slot already exists.")
        previous_title = record.title if isinstance(record, Course) else None
        record = await self.repository.update(record, changes)
        if isinstance(record, Course) and record.title != previous_title:
            await self.repository.sync_course_label(record.id, record.title)
        logger.info(
            "resource_updated kind=%s id=%s fields=%s",
            record.__tablename__,
            record.id,
            sorted(changes),
        )
        return self.response_schema.model_validate(record)


class PlannerService(MutableResourceService[StudySession, StudySessionResponse]):
    def __init__(self, repository: PlannerRepository) -> None:
        super().__init__(repository, StudySessionResponse)


class NoteService(ResourceService[Note, NoteResponse]):
    def __init__(self, repository: NoteRepository) -> None:
        super().__init__(repository, NoteResponse)

    async def patch_resource(self, resource_id: int, payload: NotePatch) -> NoteResponse:
        await self.repository.lock_owner()
        record = await self.require_resource(resource_id)
        if record.version != payload.expected_version:
            raise ApiError(
                409, "This note changed elsewhere. Review the latest version before saving."
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        await self.validate_links(changes, record)
        values = {
            name: changes.get(name, getattr(record, name))
            for name in self.repository.duplicate_fields
        }
        if await self.repository.duplicate_exists(values, exclude_id=resource_id):
            raise ApiError(409, "Another active note has this title.")
        changes["version"] = record.version + 1
        return NoteResponse.model_validate(await self.repository.update(record, changes))


class GoalService(MutableResourceService[Goal, GoalResponse]):
    def __init__(self, repository: GoalRepository) -> None:
        super().__init__(repository, GoalResponse)


class CourseService(MutableResourceService[Course, CourseResponse]):
    def __init__(self, repository: CourseRepository) -> None:
        super().__init__(repository, CourseResponse)
