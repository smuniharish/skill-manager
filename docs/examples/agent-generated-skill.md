# Generate a Skill candidate

Run the deterministic example to exercise structured extraction without
depending on a hosted model:

```console
uv run python examples/06_agent_generated_skill.py
```

It supplies a local LangChain `Runnable` fixture to the public
`generate_skill` API. Replace that fixture with a model Runnable configured
by your application for live generation. Inside an async function with
`manager` and `generator` configured:

```python
candidate = await manager.generate_skill(
    generator,
    {"request": "Create a SQL review Skill."},
)
```

## Verified result

Output from the deterministic example:

```text
agent ACTIVE
```

The generated candidate is validated before registration. Set
`require_human_approval=True` when agent-generated Skills must remain pending
until a reviewer approves them. See the
[generation guide](../guides/agent-skill-generation.md) for model setup.
