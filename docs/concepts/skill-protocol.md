# Skill protocol

Protocol version `1.0` describes a Skill independently of the installed
package version. Its frozen public model includes `skill_id`, integer
`revision`, `metadata` (name, PEP 440 version, description, tags),
`instructions`, optional `dependencies`, `capabilities`, `resources`,
`prompts`, `provenance`, `lifecycle`, and `governance`. A metadata version
identifies a release; a revision and opaque ID identify a particular
governed record. These are not interchangeable.

```python
from skill_manager import Skill, SkillDependency, SkillMetadata

skill = Skill(
    metadata=SkillMetadata(
        name="weekly-report", version="1.0", description="Write a weekly report"
    ),
    instructions=("Write a concise report.",),
    dependencies=(SkillDependency(name="collect-data", version=">=1,<2"),),
)
assert skill.api_version == "1.0"
assert skill.revision == 1
```

`SkillSource` implementations supply YAML documents; Skill Manager parses
YAML safely, validates the typed model and applies domain validation before
admitting it to the catalog. YAML is data, never executable code. Refer to
[identity](skill-id.md), [dependencies](dependencies.md), and
[governance](governance.md) for the behavioral rules behind these fields.
