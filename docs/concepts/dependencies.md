# Dependencies

Declare a dependency by Skill name and PEP 440 version specifier (for example,
`>=1,<2`). `build_bundle` resolves active dependencies transitively, placing
dependencies before the Skills that require them. The default `"*"` accepts
any available version. Registration does not execute or install dependencies.

```python
import asyncio
from skill_manager import Skill, SkillDependency, SkillManager, SkillMetadata

async def main():
    manager = SkillManager()
    await manager.register_skill(Skill(
        metadata=SkillMetadata(name="collect", version="1.0", description="Collect data"),
        instructions=("Collect the data.",),
    ))
    await manager.register_skill(Skill(
        metadata=SkillMetadata(name="report", version="1.0", description="Report data"),
        instructions=("Report the data.",),
        dependencies=(SkillDependency(name="collect", version=">=1,<2"),),
    ))
    bundle = await manager.build_bundle(["report"])
    print([skill.metadata.name for skill in bundle.skills])

asyncio.run(main())
```

Output: `['collect', 'report']`. An unavailable requirement raises
`SkillDependencyError`; a cycle raises `SkillDependencyCycleError`. Treat
these errors as catalog problems to resolve before handing a bundle to an
application runtime.
