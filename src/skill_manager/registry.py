"""Pluggable Skill registry contract and in-memory implementation."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterable

from packaging.version import InvalidVersion, Version

from skill_manager.errors import SkillConflictError, SkillNotFoundError
from skill_manager.models import Skill, SkillLifecycleState


class SkillRegistry(ABC):
    """Validated Skill catalog used by :class:`SkillManager`.

    Implementations may keep catalog state in process or persist it externally.
    They must preserve immutable revisions and reject multiple active Skills
    with the same name and version.
    """

    @abstractmethod
    async def put(self, skill: Skill) -> None:
        """Insert or idempotently replace one Skill revision."""

    @abstractmethod
    async def check_put(self, skill: Skill) -> None:
        """Validate a prospective write without mutating registry state."""

    @abstractmethod
    async def get(self, skill_id: str) -> Skill:
        """Return a Skill by immutable ID."""

    @abstractmethod
    async def by_name(self, name: str, version: str | None = None) -> Skill:
        """Return an active Skill by name and optional exact version."""

    @abstractmethod
    async def all(self, *, states: set[SkillLifecycleState] | None = None) -> tuple[Skill, ...]:
        """Return all Skills, optionally filtered by lifecycle state."""

    @abstractmethod
    async def remove(self, skill_id: str) -> Skill:
        """Remove and return one Skill revision."""

    @abstractmethod
    async def replace_lifecycle(self, skill: Skill) -> None:
        """Replace an existing Skill after a lifecycle transition."""

    async def ingest_many(self, skills: Iterable[Skill]) -> None:
        """Insert several Skills using the implementation's write semantics."""
        for skill in skills:
            await self.put(skill)


class InMemorySkillRegistry(SkillRegistry):
    """Concurrency-safe process-local Skill registry."""

    def __init__(self) -> None:
        self._by_id: dict[str, Skill] = {}
        self._by_name_version: dict[tuple[str, str], set[str]] = {}
        self._lock = asyncio.Lock()

    async def put(self, skill: Skill) -> None:
        async with self._lock:
            self._check_put(skill)
            key = (skill.metadata.name, skill.metadata.version)
            self._by_id[skill.skill_id] = skill
            self._by_name_version.setdefault(key, set()).add(skill.skill_id)

    async def check_put(self, skill: Skill) -> None:
        async with self._lock:
            self._check_put(skill)

    def _check_put(self, skill: Skill) -> None:
        key = (skill.metadata.name, skill.metadata.version)
        active_revision_ids = {
            existing_id
            for existing_id in self._by_name_version.get(key, set())
            if existing_id != skill.skill_id
            and self._by_id[existing_id].lifecycle.state is SkillLifecycleState.ACTIVE
        }
        if skill.lifecycle.state is SkillLifecycleState.ACTIVE and active_revision_ids:
            raise SkillConflictError(
                f"multiple active revisions for Skill {skill.metadata.name!r} "
                f"version {skill.metadata.version!r}"
            )
        existing = self._by_id.get(skill.skill_id)
        if existing is not None and existing.revision > skill.revision:
            raise SkillConflictError(f"stale update for Skill {skill.skill_id!r}")
        if (
            existing is not None
            and existing.revision == skill.revision
            and existing.model_dump(mode="json") != skill.model_dump(mode="json")
        ):
            raise SkillConflictError(
                f"immutable Skill revision {skill.skill_id!r} cannot be overwritten"
            )

    async def get(self, skill_id: str) -> Skill:
        async with self._lock:
            try:
                return self._by_id[skill_id]
            except KeyError as error:
                raise SkillNotFoundError(f"Skill {skill_id!r} was not found") from error

    async def by_name(self, name: str, version: str | None = None) -> Skill:
        async with self._lock:
            matches = [
                skill
                for (skill_name, skill_version), skill_ids in self._by_name_version.items()
                if skill_name == name and (version is None or skill_version == version)
                for skill_id in skill_ids
                if (skill := self._by_id[skill_id]).lifecycle.state is SkillLifecycleState.ACTIVE
            ]
            if not matches:
                raise SkillNotFoundError(f"Skill {name!r} version {version!r} was not found")
            if version is None:
                try:
                    return max(
                        matches, key=lambda item: (Version(item.metadata.version), item.skill_id)
                    )
                except InvalidVersion as error:
                    raise SkillConflictError(
                        f"invalid catalog version for Skill {name!r}"
                    ) from error
            return matches[0]

    async def all(self, *, states: set[SkillLifecycleState] | None = None) -> tuple[Skill, ...]:
        async with self._lock:
            values = tuple(self._by_id.values())
        if states is None:
            return values
        return tuple(skill for skill in values if skill.lifecycle.state in states)

    async def remove(self, skill_id: str) -> Skill:
        async with self._lock:
            try:
                skill = self._by_id.pop(skill_id)
            except KeyError as error:
                raise SkillNotFoundError(f"Skill {skill_id!r} was not found") from error
            key = (skill.metadata.name, skill.metadata.version)
            ids = self._by_name_version[key]
            ids.discard(skill_id)
            if not ids:
                self._by_name_version.pop(key)
            return skill

    async def replace_lifecycle(self, skill: Skill) -> None:
        async with self._lock:
            if skill.skill_id not in self._by_id:
                raise SkillNotFoundError(f"Skill {skill.skill_id!r} was not found")
            if skill.lifecycle.state is SkillLifecycleState.ACTIVE:
                key = (skill.metadata.name, skill.metadata.version)
                if any(
                    skill_id != skill.skill_id
                    and self._by_id[skill_id].lifecycle.state is SkillLifecycleState.ACTIVE
                    for skill_id in self._by_name_version.get(key, set())
                ):
                    raise SkillConflictError(
                        f"another active revision already exists for {skill.metadata.name!r}"
                    )
            self._by_id[skill.skill_id] = skill
