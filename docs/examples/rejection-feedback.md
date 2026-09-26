# Reject and retain a revision

Attach actionable reviewer feedback to a pending candidate:

Inside the async review handler:

```python
rejected = await manager.reject_skill(
    candidate.skill_id,
    feedback="Include rollback and isolation-level guidance.",
    metadata={"reviewer": "developer", "severity": "high"},
)
retained = await manager.list_rejected_skills()
```

Run the deterministic lifecycle example:

```console
uv run python examples/12_rejection_feedback.py
```

## Verified result

Output:

```text
state=REJECTED retained_revisions=1
```

Rejection retains the revision for review; it does not regenerate or approve
a replacement. For an application-controlled correction loop, see the
[feedback-informed regeneration example](feedback-informed-regeneration.md).
