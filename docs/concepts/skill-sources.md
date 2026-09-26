# Skill sources

`SkillSource` is the public async contract for loading YAML documents and
saving/deleting validated Skills. Supply one or more sources to
`SkillManager(sources=[...])`. The built-in `FilesystemSkillSource` stores
Skill documents under the configured root; applications can implement a
database, Git, or other origin using the same contract.

```python
import asyncio
from skill_manager import (
    FilesystemSkillSource, Skill, SkillManager, SkillMetadata
)

async def main():
    manager = SkillManager(sources=[FilesystemSkillSource("skills")])
    saved = await manager.register_skill(Skill(
        metadata=SkillMetadata(
            name="outline", version="1.0", description="Outline a document"
        ),
        instructions=("Create a short outline.",),
    ))
    print((await manager.load(saved.skill_id)).metadata.name)

asyncio.run(main())
```

Output: `outline`. This example persists a document to the configured source;
choose a project-specific location in your application. Source IDs must be
unique. Invalid records are isolated and exposed through
`manager.source_errors`; healthy sources remain usable. A refresh reports
source failures without discarding successful loads. Sources provide
documents; the [registry](registry.md) holds the validated operational
catalog and can be customized independently.
