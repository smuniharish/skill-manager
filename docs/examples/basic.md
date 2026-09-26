# Register a Skill and build a bundle

Use this flow when an application already has a validated Skill definition and
wants its resolved instructions:

In an async application workflow:

```python
from skill_manager import Skill, SkillManager, SkillMetadata

manager = SkillManager()
skill = Skill(
    metadata=SkillMetadata(
        name="postgres-analysis",
        version="1.0.0",
        description="Analyze PostgreSQL query plans.",
    ),
    instructions=("Use the postgres-analysis capability safely.",),
)
await manager.register_skill(skill)
bundle = await manager.build_bundle([skill])
print(bundle.instructions)
```

Run the complete example from the project root:

```console
uv run python examples/01_basic_skill.py
```

## Verified result

Output:

```text
('Use the postgres-analysis capability safely.',)
```

The bundle contains Skill-domain instructions and resolved requirements; an
agent framework or application decides how to consume them.
Next, [persist a Skill](filesystem-source.md) or
[discover candidates](dynamic-discovery.md).
