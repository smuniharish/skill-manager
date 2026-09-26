# Registry

The registry is the validated operational catalog used for lookup, discovery,
dependency resolution and lifecycle changes. `SkillRegistry` is its public
async extension point; `InMemorySkillRegistry` is the concurrency-safe
process-local default.

```python
import asyncio
from skill_manager import (
    InMemorySkillRegistry, Skill, SkillManager, SkillMetadata
)

async def main():
    manager = SkillManager(registry=InMemorySkillRegistry())
    await manager.register_skill(Skill(
        metadata=SkillMetadata(
            name="edit", version="1.0", description="Edit a draft"
        ),
        instructions=("Edit for clarity.",),
    ))
    print([skill.metadata.name for skill in await manager.list_active_skills()])

asyncio.run(main())
```

Output: `['edit']`. A custom registry must implement insertion checks,
lookup by ID and active name/version, lifecycle filtering and replacement,
and removal; it must preserve immutable revisions and reject competing
active records for the same name/version. A [SkillSource](skill-sources.md)
supplies documents and optionally persists records, whereas the registry
indexes validated Skills. You can inject one or both. See the
[PostgreSQL example](../examples/postgres-source.md) for a durable registry.
