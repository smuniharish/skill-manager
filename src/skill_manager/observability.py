"""Provider-neutral observability events for the Skill domain."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

type SkillObservabilityValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class SkillObservabilityEvent:
    """One sanitized Skill lifecycle event."""

    name: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    attributes: Mapping[str, SkillObservabilityValue] = field(default_factory=dict)


@runtime_checkable
class SkillObservabilitySink(Protocol):
    """Application-owned destination for Skill lifecycle telemetry."""

    async def emit(self, event: SkillObservabilityEvent) -> None: ...


class NoOpSkillObservabilitySink:
    """Default sink that performs no external I/O."""

    async def emit(self, event: SkillObservabilityEvent) -> None:
        del event


__all__ = [
    "NoOpSkillObservabilitySink",
    "SkillObservabilityEvent",
    "SkillObservabilitySink",
    "SkillObservabilityValue",
]
