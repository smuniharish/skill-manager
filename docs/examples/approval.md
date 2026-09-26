# Approve a pending Skill

When the manager requires human approval, make the decision against the
candidate's immutable Skill ID:

Inside the async review handler:

```python
approved = await manager.approve_skill(
    candidate.skill_id,
    metadata={"reviewer": "developer", "reason": "Reviewed"},
)
print(approved.lifecycle.state.value)
```

This is an excerpt; `candidate` is a pending agent-origin Skill. Run the
complete deterministic example:

```console
uv run python examples/11_approval.py
```

## Verified result

Output:

```text
ACTIVE
```

The example configures `require_human_approval=True`, registers an
agent-origin candidate, and explicitly approves it. Approval is recorded as
Skill lifecycle state; it does not authorize or sandbox agent execution.
For rejection and correction, see [rejection feedback](rejection-feedback.md).
