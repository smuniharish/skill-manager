# Requiring human approval

Require review for agent-generated Skills by setting the policy on
`SkillManagerConfig`:

```python
from skill_manager import SkillManager, SkillManagerConfig

manager = SkillManager(
    config=SkillManagerConfig(require_human_approval=True),
)
candidate = await manager.generate_skill(generator, request)
assert candidate.lifecycle.state.value == "PENDING_APPROVAL"

active = await manager.approve_skill(
    candidate.skill_id,
    metadata={"reviewer": "skill-owner", "reason": "Reviewed for release"},
)
```

This is an async application excerpt; `generator` and `request` are the
application's configured model input. Agent-created candidates remain
unavailable to discovery until approved. Human-authored Skills are not
automatically made pending by this policy. Rejections retain the revision and
record review feedback; see the
[rejection feedback guide](rejection-feedback.md).

The
[approval example](../examples/approval.md) verifies that explicit approval
moves a candidate to `ACTIVE`. Approval is a Skill lifecycle decision, not a
security boundary for executing agent behavior; the application remains
responsible for authorization and runtime controls.
