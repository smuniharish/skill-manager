# Skills

A `Skill` is validated, declarative data: instructions, metadata, optional
dependencies and capability requirements, resource references, prompts,
provenance, lifecycle state, and governance references. Skill Manager owns
this domain. It does **not** execute the instructions or create an agent;
your LangChain or LangGraph application decides how to use a resolved
[bundle](skill-bundles.md).

Create a Skill with the public models, then register it:

```python
import asyncio
from skill_manager import Skill, SkillManager, SkillMetadata

async def main():
    manager = SkillManager()
    skill = await manager.register_skill(
        Skill(
            metadata=SkillMetadata(
                name="summarize-notes",
                version="1.0",
                description="Summarize meeting notes",
            ),
            instructions=("Summarize the notes in three bullets.",),
        )
    )
    print((await manager.load("summarize-notes")).skill_id == skill.skill_id)
    print([item.metadata.name for item in await manager.discover("summarize")])

asyncio.run(main())
```

Output:

```text
True
['summarize-notes']
```

With no source, registration lives in the default in-memory catalog for the
life of the manager. Supply a [source](skill-sources.md) for persistence.
Models are frozen: create a new revision rather than editing a Skill in place.
