# Rejection

Reject a `PENDING_APPROVAL` revision by its immutable ID, with a nonempty
reason. Skill Manager submits a rejection event to `feedback-manager`
before transitioning the Skill to `REJECTED`.

```python
import asyncio
from skill_manager import (
    Skill, SkillManager, SkillManagerConfig, SkillMetadata,
    SkillOrigin, SkillProvenance,
)

async def main():
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    pending = await manager.register_skill(Skill(
        metadata=SkillMetadata(name="draft", version="1.0", description="Draft text"),
        instructions=("Draft the text.",),
        provenance=SkillProvenance(origin=SkillOrigin.AGENT),
    ))
    rejected = await manager.reject_skill(
        pending.skill_id, feedback="Needs source citations"
    )
    print((await manager.load(rejected.skill_id)).lifecycle.state.value)
    print(len(await manager.list_rejected_skills()))

asyncio.run(main())
```

Output:

```text
REJECTED
1
```

Rejected revisions remain addressable for audit, cannot enter a bundle,
cannot be removed through `remove_skill`, and are not silently reactivated.
Feedback failure raises `SkillRejectionError` without completing the Skill
transition. To correct a rejection, create a new linked revision; see the
[feedback loop](feedback-loop.md).
