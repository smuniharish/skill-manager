# Feedback loop

Review feedback is evidence for the **next** candidate, not permission to
change policy or rewrite a previous Skill. Skill Manager submits
approval/rejection events targeted at the exact Skill ID through
`feedback-manager`; the external package owns event persistence and lifecycle.
The Skill domain owns the approval gate and Skill lifecycle.

After rejecting a pending revision, an application may explicitly request a
new one with `generate_skill(generator, input, parent_skill_id=rejected.skill_id)`.
The manager retrieves prior rejection events for that parent and passes the
feedback to structured generation as `previous_skill_feedback` for mapping
inputs (or appended context for other inputs). It then validates the
candidate and applies the same governance rules to the new revision.

Rejection **does not** invoke generation automatically. The rejected record
remains available via `load(skill_id)` and
`list_rejected_skills()`; with approval required, the corrected agent
revision again starts pending. Supply an application-configured LangChain
`Runnable` for generation—Skill Manager does not own the model or agent
execution.
