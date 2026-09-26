# Skill bundles

Call `build_bundle` with at least one active Skill or name/ID. The result is
frozen, resolved **data**: dependency-ordered Skills and instructions,
dependency declarations, selected capabilities, resource references,
prompts, and provenance. The application chooses which parts to give its
agent or graph. Building a bundle never executes a Skill.

```python
import asyncio
from skill_manager import Skill, SkillManager, SkillMetadata

async def main():
    manager = SkillManager()
    await manager.register_skill(
        Skill(
            metadata=SkillMetadata(
                name="answer", version="1.0", description="Answer questions"
            ),
            instructions=("Answer with supporting evidence.",),
        )
    )
    bundle = await manager.build_bundle(["answer"])
    print([skill.metadata.name for skill in bundle.skills])
    print(bundle.instructions)

asyncio.run(main())
```

Output:

```text
['answer']
('Answer with supporting evidence.',)
```

The consuming application controls agent context and execution. Missing
dependencies or required MCP capabilities fail bundle construction rather
than producing an incomplete result; see [dependencies](dependencies.md)
and [capabilities](capabilities.md).
