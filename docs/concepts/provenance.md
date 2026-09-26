# Provenance

`SkillProvenance` records **Skill-domain** lineage: origin (`human`, `agent`,
`imported`, or `system`), timezone-aware creation time, optional source,
generation context, and parent Skill IDs. Use parent IDs to relate a
corrected revision to its predecessor without modifying the older record.

```python
from skill_manager import Skill, SkillMetadata, SkillOrigin, SkillProvenance

skill = Skill(
    metadata=SkillMetadata(name="review", version="1.0", description="Review a draft"),
    instructions=("Check the draft for clarity.",),
    provenance=SkillProvenance(origin=SkillOrigin.HUMAN, source="editorial"),
)
assert skill.provenance.origin is SkillOrigin.HUMAN
```

Do not put credentials in provenance source URLs or generation context.
Execution tracing and explanation for an application LangGraph belong to
`langgraph-xai`, not to this Skill record. The application can carry Skill
IDs into its graph context when correlating the two.
