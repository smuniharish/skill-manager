# Catalog lifecycle and provenance views

`examples/25_catalog_views.py` demonstrates the public catalog query methods.
In an async application function with a populated `manager`:

```python
all_revisions = await manager.list_skills()
active = await manager.list_active_skills()
approved = await manager.list_approved_skills()
pending = await manager.list_pending_skills()
rejected = await manager.list_rejected_skills()
agent_generated = await manager.list_agent_generated_skills()
human_authored = await manager.list_human_authored_skills()
```

`list_skills` supports combined lifecycle and provenance filters. With the
same populated manager:

```python
rejected_agent_revisions = await manager.list_skills(
    states={SkillLifecycleState.REJECTED},
    origins={SkillOrigin.AGENT},
)
```

The provenance-specific convenience methods also accept `states=`:

```python
active_agent_revisions = await manager.list_agent_generated_skills(
    states={SkillLifecycleState.ACTIVE},
)
```

## Active versus approved

These terms are intentionally different:

- **active** means the revision is available for discovery and bundle
  construction, regardless of whether it was human-authored or approved.
- **approved** means the revision is active and its governance record contains
  a human approval event ID.
- **agent-generated** describes provenance and can include pending, approved,
  active-without-approval when policy allows it, and rejected revisions.

This distinction prevents human-authored active Skills from being
misrepresented as having passed an approval event.

## Run

```console
uv run python examples/25_catalog_views.py
```

## Verified result

Output:

```text
active=2 approved=1 pending=1 rejected=1 agent_generated=3 human_authored=1
```

For review decisions, see [approval](approval.md) and
[rejection feedback](rejection-feedback.md).
