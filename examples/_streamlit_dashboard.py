"""Synchronous service layer for the Streamlit lifecycle dashboard."""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import yaml
from feedback_manager import (
    FeedbackEvent,
    FeedbackManager,
    FeedbackNotFoundError,
    FeedbackQuery,
    FeedbackStatus,
    FeedbackStoreError,
    validate_transition,
)
from feedback_manager.contracts.store import FeedbackStore

from skill_manager import (
    DefaultSkillValidator,
    FilesystemSkillSource,
    Skill,
    SkillLifecycleState,
    SkillManager,
    SkillManagerConfig,
    SkillMetadata,
    SkillOrigin,
    SkillProvenance,
)
from skill_manager.validation import parse_skill_yaml

T = TypeVar("T")


class SQLiteFeedbackStore(FeedbackStore):
    """Small durable feedback store for the single-process example UI."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS feedback_events (
                    feedback_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    document TEXT NOT NULL
                )
                """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _get_sync(self, feedback_id: UUID) -> FeedbackEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document FROM feedback_events WHERE feedback_id = ?",
                (str(feedback_id),),
            ).fetchone()
        return FeedbackEvent.model_validate_json(row[0]) if row is not None else None

    async def create(self, feedback: FeedbackEvent) -> FeedbackEvent:
        async with self._lock:
            return await asyncio.to_thread(self._create_sync, feedback)

    def _create_sync(self, feedback: FeedbackEvent) -> FeedbackEvent:
        with self._connect() as connection:
            if feedback.idempotency_key is not None:
                row = connection.execute(
                    "SELECT document FROM feedback_events WHERE idempotency_key = ?",
                    (feedback.idempotency_key,),
                ).fetchone()
                if row is not None:
                    return FeedbackEvent.model_validate_json(row[0])
            try:
                connection.execute(
                    """
                    INSERT INTO feedback_events (
                        feedback_id, idempotency_key, created_at, document
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(feedback.feedback_id),
                        feedback.idempotency_key,
                        feedback.created_at.isoformat(),
                        feedback.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise FeedbackStoreError(
                    "a feedback event with this id already exists",
                    feedback_id=feedback.feedback_id,
                ) from error
        return feedback

    async def get(self, feedback_id: UUID) -> FeedbackEvent | None:
        async with self._lock:
            return await asyncio.to_thread(self._get_sync, feedback_id)

    async def update(self, feedback: FeedbackEvent) -> FeedbackEvent:
        async with self._lock:
            updated = await asyncio.to_thread(self._update_sync, feedback)
        return updated

    def _update_sync(self, feedback: FeedbackEvent) -> FeedbackEvent:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE feedback_events SET document = ? WHERE feedback_id = ?",
                (feedback.model_dump_json(), str(feedback.feedback_id)),
            )
            if cursor.rowcount == 0:
                raise FeedbackNotFoundError(
                    "cannot update a feedback event that was never created",
                    feedback_id=feedback.feedback_id,
                )
        return feedback

    async def transition(
        self,
        feedback_id: UUID,
        status: FeedbackStatus,
    ) -> FeedbackEvent:
        async with self._lock:
            current = await asyncio.to_thread(self._get_sync, feedback_id)
            if current is None:
                raise FeedbackNotFoundError(
                    "cannot transition an unknown feedback event",
                    feedback_id=feedback_id,
                )
            validate_transition(feedback_id, current.status, status)
            updated = current.with_status(status)
            return await asyncio.to_thread(self._update_sync, updated)

    async def query(self, query: FeedbackQuery) -> list[FeedbackEvent]:
        events = await self.list()
        matches = [event for event in events if query.matches(event)]
        return matches[: query.limit] if query.limit is not None else matches

    async def list(self) -> list[FeedbackEvent]:
        async with self._lock:
            return await asyncio.to_thread(self._list_sync)

    def _list_sync(self) -> list[FeedbackEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT document FROM feedback_events ORDER BY created_at, feedback_id"
            ).fetchall()
        return [FeedbackEvent.model_validate_json(row[0]) for row in rows]


class AsyncWorker:
    """Own one event loop so async dependencies survive Streamlit reruns."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run(self, coroutine: Coroutine[Any, Any, T]) -> T:
        future: Future[T] = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        return future.result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


class SkillDashboard:
    """UI-facing facade built only from public package APIs."""

    def __init__(self, root: Path) -> None:
        self.worker = AsyncWorker()
        self.source = FilesystemSkillSource(root, source_id="streamlit")
        self.feedback = FeedbackManager(store=SQLiteFeedbackStore(root / "feedback.sqlite3"))
        self.manager = SkillManager(
            sources=[self.source],
            config=SkillManagerConfig(
                allow_agent_skill_creation=True,
                require_human_approval=True,
            ),
            feedback_manager=self.feedback,
        )
        self.refresh()

    def refresh(self) -> None:
        self.worker.run(self.manager.refresh())

    def skills(self) -> tuple[Skill, ...]:
        values = self.worker.run(self.manager.list_skills())
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.lifecycle.state.value,
                    item.metadata.name,
                    item.metadata.version,
                ),
            )
        )

    def source_documents(self) -> dict[str, str]:
        return dict(self.worker.run(self.source.load()))

    def create_candidate(
        self,
        *,
        name: str,
        version: str,
        description: str,
        instructions: tuple[str, ...],
        tags: tuple[str, ...],
    ) -> Skill:
        candidate = Skill(
            metadata=SkillMetadata(
                name=name,
                version=version,
                description=description,
                tags=tags,
            ),
            instructions=instructions,
            provenance=SkillProvenance(
                origin=SkillOrigin.AGENT,
                source="streamlit-manual-candidate",
            ),
        )
        return self.worker.run(
            self.manager.register_skill(candidate, source_id=self.source.source_id)
        )

    def generate_candidate(
        self,
        *,
        request: str,
        api_key: str,
        model: str,
        base_url: str,
    ) -> Skill:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
        )
        return self.worker.run(
            self.manager.generate_skill(
                llm,
                request,
                source_id=self.source.source_id,
                repair_generator=llm,
            )
        )

    def approve(self, skill_id: str, *, reviewer: str, reason: str) -> Skill:
        return self.worker.run(
            self.manager.approve_skill(
                skill_id,
                metadata={"reviewer": reviewer, "reason": reason},
            )
        )

    def reject(self, skill_id: str, *, reviewer: str, feedback: str) -> Skill:
        return self.worker.run(
            self.manager.reject_skill(
                skill_id,
                feedback=feedback,
                metadata={"reviewer": reviewer},
            )
        )

    def validate_yaml(self, document: str) -> Skill:
        return parse_skill_yaml(document, DefaultSkillValidator())

    def import_yaml(self, document: str) -> Skill:
        skill = self.validate_yaml(document)
        return self.worker.run(self.manager.register_skill(skill, source_id=self.source.source_id))

    def feedback_events(self, skill_id: str | None = None) -> list[dict[str, Any]]:
        query = FeedbackQuery(
            target_type="skill" if skill_id else None,
            target_id=skill_id,
            limit=100,
        )
        events = self.worker.run(self.feedback.query(query))
        return [event.model_dump(mode="json") for event in reversed(events)]

    @staticmethod
    def yaml(skill: Skill) -> str:
        return yaml.safe_dump(
            skill.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        )

    def counts(self) -> dict[SkillLifecycleState, int]:
        result = {state: 0 for state in SkillLifecycleState}
        for skill in self.skills():
            result[skill.lifecycle.state] += 1
        return result

    def close(self) -> None:
        self.worker.run(self.manager.close())
        self.worker.close()


__all__ = ["SkillDashboard"]
