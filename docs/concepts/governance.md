# Governance

`SkillManagerConfig` is immutable manager policy, not an instruction to a
model. Its defaults allow agent creation and do not require human approval.
Pass one config object to the manager:

```python
from skill_manager import SkillManager, SkillManagerConfig

manager = SkillManager(config=SkillManagerConfig(
    allow_agent_skill_creation=False,
    require_human_approval=True,
))
```

With creation disabled, `generate_skill` and agent-origin registration are
rejected with `SkillCreationDisabledError`; agent-origin source records
cannot enter the catalog either. Human-origin Skills are not subject to
this agent-only approval policy. When creation is allowed and approval
required, agent-origin revisions enter `PENDING_APPROVAL` and cannot be
discovered or bundled until explicitly approved. A source record claiming
approval is checked against a matching resolved feedback event rather than
trusted on its own.

Approval or rejection requires successful event processing by
`feedback-manager` before the Skill state changes. Use
[approval](approval.md) and [rejection](rejection.md) for complete workflows.
