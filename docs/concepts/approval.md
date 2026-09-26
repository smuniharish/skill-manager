# Approval

Configure human approval for agent-origin Skills using
`SkillManagerConfig(require_human_approval=True)`. A newly registered agent
revision becomes `PENDING_APPROVAL`, not discoverable or bundle-ready.
Approval uses its **immutable ID** so another version cannot accidentally
be activated.

```python
import asyncio
from skill_manager import (
    Skill, SkillManager, SkillManagerConfig, SkillMetadata,
    SkillOrigin, SkillProvenance,
)

async def main():
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    pending = await manager.register_skill(Skill(
        metadata=SkillMetadata(
            name="draft-reply", version="1.0", description="Draft a reply"
        ),
        instructions=("Write a concise reply.",),
        provenance=SkillProvenance(origin=SkillOrigin.AGENT),
    ))
    print(pending.lifecycle.state.value)
    approved = await manager.approve_skill(
        pending.skill_id, metadata={"reviewer": "team-lead"}
    )
    print(approved.lifecycle.state.value)

asyncio.run(main())
```

Output:

```text
PENDING_APPROVAL
ACTIVE
```

The approval feedback event must succeed before activation. Failure raises
`SkillApprovalError` and does not activate the revision. The approval rule
targets agent-origin Skills; human-origin Skills remain active by default.
See [governance](governance.md) for the creation gate.
