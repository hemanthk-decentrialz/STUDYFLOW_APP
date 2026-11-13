import asyncio
import json
import logging
import tempfile
from datetime import UTC, datetime
from typing import BinaryIO

from app.models.course import Course
from app.models.focus_session import FocusSession
from app.models.goal import Goal
from app.models.note import Note
from app.models.settings import Settings
from app.models.study_session import StudySession
from app.models.timer import Timer
from app.repositories.settings import SettingsRepository
from app.schemas.resources import Page
from app.schemas.settings import (
    DeletedResource,
    ReminderResponse,
    SettingsPatchRequest,
    SettingsState,
    TrashParams,
)

logger = logging.getLogger("studyflow.services.settings")


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self.repository = repository
        self._settings: SettingsState | None = None

    async def get_settings(self) -> SettingsState:
        if self._settings is None:
            stored = await self.repository.get()
            self._settings = (
                SettingsState.model_validate({"theme": stored.theme, **stored.preferences})
                if stored
                else SettingsState()
            )
        return self._settings

    async def patch_settings(self, payload: SettingsPatchRequest) -> SettingsState:
        logger.info("preferences_update_started")
        await self.repository.lock_owner()
        current = await self.get_settings()
        validated = SettingsState.model_validate(
            current.model_dump() | payload.settings.model_dump(exclude_unset=True)
        )
        await self.repository.save(
            Settings(
                user_id=self.repository.user_id,
                theme=validated.theme,
                preferences=validated.model_dump(exclude={"theme"}),
            )
        )
        self._settings = validated
        return validated

    async def deleted_page(self, params: TrashParams) -> Page[DeletedResource]:
        rows, total = await self.repository.deleted_page(
            params.page, params.limit, params.kind, params.search, params.order
        )
        return Page(
            items=[DeletedResource.model_validate(row) for row in rows],
            page=params.page,
            limit=params.limit,
            total=total,
            total_pages=(total + params.limit - 1) // params.limit,
        )

    async def reminders(self) -> list[ReminderResponse]:
        settings = await self.get_settings()
        rows = await self.repository.due_reminders(
            datetime.now(UTC),
            settings.timeZone,
            settings.reminderLeadMinutes,
            settings.sessionReminders,
            settings.deadlineReminders,
        )
        return [ReminderResponse.model_validate(row) for row in rows]

    async def export_data(self) -> BinaryIO:
        # Complete the DB work before response headers; keep memory bounded with a temp file.
        await self.repository.lock_owner()
        output = await asyncio.to_thread(tempfile.TemporaryFile, mode="w+b")

        buffer = bytearray()

        async def write(text: str) -> None:
            buffer.extend(text.encode("utf-8"))
            if len(buffer) >= 65536:
                await asyncio.to_thread(output.write, bytes(buffer))
                buffer.clear()

        try:
            await write(
                '{\n  "formatVersion": 1,\n  "exportedAt": '
                + json.dumps(datetime.now(UTC).isoformat())
            )
            for name, model in (
                ("preferences", Settings),
                ("courses", Course),
                ("notes", Note),
                ("goals", Goal),
                ("studySessions", StudySession),
                ("focusSessions", FocusSession),
                ("timer", Timer),
            ):
                await write(',\n  "' + name + '": [')
                first = True
                async for row in self.repository.export_rows(model):
                    await write(
                        ("\n" if first else ",\n")
                        + "    "
                        + json.dumps(
                            row, default=str, ensure_ascii=False, allow_nan=False, indent=2
                        ).replace("\n", "\n    ")
                    )
                    first = False
                await write("]" if first else "\n  ]")
            await write("\n}\n")
            if buffer:
                await asyncio.to_thread(output.write, bytes(buffer))
            await asyncio.to_thread(output.seek, 0)
            logger.info("study_data_export_prepared")
            return output
        except BaseException:
            await asyncio.to_thread(output.close)
            raise
