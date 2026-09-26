# Rejecting a Skill revision

Reject a pending revision by its immutable Skill ID and record actionable
reviewer context:

```python
rejected = await manager.reject_skill(
    candidate.skill_id,
    feedback="Add rollback verification and state the isolation assumptions.",
    metadata={"reviewer": "database-owner", "severity": "high"},
)
assert rejected.lifecycle.state.value == "REJECTED"
```

The rejected revision remains available for audit and is not edited in place.
Rejection does not call a model or create a replacement. If the application
chooses to request a correction, it can pass the rejected ID as
`parent_skill_id` to `generate_skill`; the new candidate still follows the
configured approval policy.

The focused
[rejection example](../examples/rejection-feedback.md) verifies retention.
The
[feedback-informed regeneration example](../examples/feedback-informed-regeneration.md)
shows the complete human-reviewed correction loop and its asserted
invariants.
