"""OpenTelemetry adapters used by the live Grafana example."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from feedback_manager.observability import ObservabilityEvent
from opentelemetry.trace import Tracer
from refresh_engine import RefreshEvent

from skill_manager import SkillObservabilityEvent


def _attributes(values: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    return {
        key: value if isinstance(value, (str, int, float, bool)) else str(value)
        for key, value in values.items()
        if value is not None
    }


class OpenTelemetrySkillSink:
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    async def emit(self, event: SkillObservabilityEvent) -> None:
        with self._tracer.start_as_current_span(event.name) as span:
            span.set_attributes(_attributes(event.attributes))
            span.set_attribute("skill.event.occurred_at", event.occurred_at.isoformat())


class OpenTelemetryFeedbackSink:
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    def emit(self, event: ObservabilityEvent) -> None:
        with self._tracer.start_as_current_span(event.name) as span:
            span.set_attribute("feedback.id", str(event.feedback_id))
            span.set_attribute("feedback.event.occurred_at", event.occurred_at.isoformat())
            span.set_attributes(_attributes(event.attributes))


class OpenTelemetryMCPMetrics:
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    async def record(
        self,
        event: str,
        *,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        with self._tracer.start_as_current_span(f"mcp.{event}") as span:
            span.set_attributes(_attributes(attributes or {}))


class OpenTelemetryRefreshHandler:
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    def __call__(self, event: RefreshEvent) -> None:
        with self._tracer.start_as_current_span(f"refresh.{event.kind.value}") as span:
            if event.refresh_id is not None:
                span.set_attribute("refresh.id", event.refresh_id)
            if event.resource_id is not None:
                span.set_attribute("refresh.resource_id", event.resource_id)
            span.set_attribute("refresh.event.occurred_at", event.timestamp.isoformat())
            span.set_attributes(_attributes(event.attributes))


__all__ = [
    "OpenTelemetryFeedbackSink",
    "OpenTelemetryMCPMetrics",
    "OpenTelemetryRefreshHandler",
    "OpenTelemetrySkillSink",
]
