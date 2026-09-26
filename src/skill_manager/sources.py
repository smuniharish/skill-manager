"""Skill source extension point and safe filesystem implementation."""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml

from skill_manager.errors import SkillSourceError
from skill_manager.models import Skill


class SkillSource(ABC):
    """Where Skills originate; each source owns its own persistence."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Return a stable, non-secret source identifier."""

    @abstractmethod
    async def load(self) -> Mapping[str, str]:
        """Return source locator to YAML text, without parsing or executing it."""

    @abstractmethod
    async def save(self, skill: Skill) -> None:
        """Persist one validated Skill revision."""

    @abstractmethod
    async def delete(self, skill_id: str) -> None:
        """Remove a persisted Skill revision by immutable ID."""


class FilesystemSkillSource(SkillSource):
    """Read and atomically write YAML files beneath a configured root."""

    def __init__(self, root: str | Path, *, source_id: str = "filesystem") -> None:
        self._root = Path(root).expanduser().resolve()
        if (
            not source_id.strip()
            or len(source_id) > 128
            or any(character in source_id for character in "\r\n\x00")
        ):
            raise ValueError("source_id must be a non-empty safe identifier")
        self._source_id = source_id

    @property
    def source_id(self) -> str:
        return self._source_id

    async def load(self) -> Mapping[str, str]:
        try:
            return await asyncio.to_thread(self._load_sync)
        except OSError as error:
            raise SkillSourceError(
                f"cannot load filesystem Skill source {self.source_id!r}"
            ) from error

    def _load_sync(self) -> dict[str, str]:
        if not self._root.exists():
            return {}
        if not self._root.is_dir():
            raise SkillSourceError(f"Skill source root is not a directory: {self._root}")
        result: dict[str, str] = {}
        for path in sorted((*self._root.glob("*.yaml"), *self._root.glob("*.yml"))):
            if path.is_symlink():
                raise SkillSourceError(
                    f"symbolic links are not allowed in Skill sources: {path.name}"
                )
            resolved = path.resolve()
            if not resolved.is_relative_to(self._root):
                raise SkillSourceError(f"Skill path escapes configured root: {path.name}")
            result[path.name] = resolved.read_text(encoding="utf-8")
        return result

    async def save(self, skill: Skill) -> None:
        try:
            await asyncio.to_thread(self._save_sync, skill)
        except OSError as error:
            raise SkillSourceError(f"cannot persist Skill {skill.skill_id!r}") from error

    def _save_sync(self, skill: Skill) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        if self._root.is_symlink():
            raise SkillSourceError("configured Skill source root may not be a symbolic link")
        destination = self._root / f"{skill.skill_id}.yaml"
        if not destination.resolve().is_relative_to(self._root):
            raise SkillSourceError("Skill destination escapes configured root")
        serialized = yaml.safe_dump(
            skill.model_dump(mode="json"), allow_unicode=True, sort_keys=True
        )
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._root,
            prefix=".skill-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            temporary_path.replace(destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    async def delete(self, skill_id: str) -> None:
        from skill_manager.models import _ID_PATTERN

        if not _ID_PATTERN.fullmatch(skill_id):
            raise SkillSourceError("invalid Skill ID for filesystem deletion")
        try:
            await asyncio.to_thread(self._delete_sync, skill_id)
        except OSError as error:
            raise SkillSourceError(f"cannot delete Skill {skill_id!r}") from error

    def _delete_sync(self, skill_id: str) -> None:
        if not self._root.exists():
            return
        for path in (*self._root.glob("*.yaml"), *self._root.glob("*.yml")):
            if path.is_symlink() or not path.resolve().is_relative_to(self._root):
                raise SkillSourceError(f"unsafe Skill source path: {path.name}")
            try:
                value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if isinstance(value, dict) and value.get("skill_id") == skill_id:
                path.unlink()
