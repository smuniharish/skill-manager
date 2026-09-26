# Lifecycle

Only three Skill states are supported:

| State | Meaning | Discovery and bundles |
|---|---|---|
| `ACTIVE` | Available to consuming applications | Eligible |
| `PENDING_APPROVAL` | Agent revision awaiting an explicit review decision | Excluded |
| `REJECTED` | Retained for audit and future revision context | Excluded |

With default config, registered human and agent Skills can be active.
With `require_human_approval=True`, agent-origin candidates are pending;
`approve_skill(skill_id)` activates one pending revision after successful
feedback processing, while `reject_skill(skill_id, feedback=...)` rejects
one. Rejected revisions cannot be silently reactivated or removed by
`remove_skill`. With creation disabled, agent candidates cannot enter
through registration, generation, or a configured source.

To make a correction, create a new Skill with its own ID, incremented
revision and parent lineage. The previous record remains addressable.
See [identity](../concepts/skill-id.md) and
[governance](governance.md).
