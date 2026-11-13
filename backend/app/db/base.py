"""Import every model here so Alembic sees the complete metadata registry."""

from app.db.base_class import Base
from app.models.auth_session import AuthSession
from app.models.course import Course
from app.models.focus_session import FocusSession
from app.models.goal import Goal
from app.models.job import Job
from app.models.note import Note
from app.models.settings import Settings
from app.models.study_session import StudySession
from app.models.timer import Timer
from app.models.user import User

__all__ = [
    "AuthSession",
    "Base",
    "Course",
    "Goal",
    "FocusSession",
    "Job",
    "Note",
    "Settings",
    "StudySession",
    "Timer",
    "User",
]
