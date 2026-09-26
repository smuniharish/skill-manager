# Feedback boundary

Skill Manager enforces creation/approval policy and owns the Skill lifecycle.
`feedback-manager` owns approval and rejection event storage, processing,
and provenance correlation. Each review targets an immutable `skill_id`;
the manager changes the corresponding pending Skill only after the event
succeeds. A failure to persist or process feedback does not authorize a
Skill transition. A rejected revision remains available for audit.

For execution provenance, applications construct
`FeedbackManager(xai_runtime=runtime)` and inject it through
`SkillManager(feedback_manager=...)`. The feedback package owns its XAI
provenance adapter; Skill Manager does not duplicate that configuration.
Graph instrumentation itself is an application/`langgraph-xai` choice, not
a requirement for Skill approval and rejection.

Feedback can inform explicit future generation via
`generate_skill(..., parent_skill_id=...)`, but cannot modify the earlier
Skill, change policy, or trigger automatic learning. See
[approval](../concepts/approval.md),
[rejection](../concepts/rejection.md), and
[feedback loop](../concepts/feedback-loop.md).
