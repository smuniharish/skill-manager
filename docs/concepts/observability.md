# Observability

Skill Manager emits sanitized, provider-neutral lifecycle events through the
`SkillObservabilitySink` protocol. The default
`NoOpSkillObservabilitySink` performs no external I/O.

The event stream covers:

- `skill.registered`
- `skill.approved`
- `skill.rejected`
- `skill.discovery.completed`
- `skill.bundle.built`
- `skill.refresh.completed`

Events contain bounded Skill-domain metadata such as immutable Skill ID,
name, version, lifecycle state, result counts, and capability counts. Raw
prompts, Skill instructions, model responses, credentials, and discovery
queries are not emitted.

Applications own their telemetry backend. An application can implement the
sink with OpenTelemetry and export to Grafana, or route events to another
existing observability platform:

```python
import asyncio
from skill_manager import (
    Skill, SkillManager, SkillMetadata, SkillObservabilitySink
)

class CollectEvents(SkillObservabilitySink):
    def __init__(self):
        self.names = []

    async def emit(self, event):
        self.names.append(event.name)

async def main():
    sink = CollectEvents()
    manager = SkillManager(observability_sink=sink)
    await manager.register_skill(Skill(
        metadata=SkillMetadata(name="outline", version="1.0", description="Outline text"),
        instructions=("Write an outline.",),
    ))
    print(sink.names)

asyncio.run(main())
```

Output: `['skill.registered']`.

Telemetry failures do not replay or reverse successful Skill-domain writes.
They are logged and exposed through `manager.observability_errors`, allowing
the application to alert without risking duplicate registration or lifecycle
transitions.

Ecosystem telemetry remains with its owner:

- `FeedbackManager(observability_sink=...)` emits feedback lifecycle events.
- `XAIRuntime.register(ObservabilityProvider, ...)` emits execution events.
- `MCPRuntime(metrics=...)` emits capability-operation metrics.
- `RefreshEngine(events=...)` publishes refresh lifecycle events.

Skill Manager does not wrap or replace those extension points.
