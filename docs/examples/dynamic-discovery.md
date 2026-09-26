# Find Skills for a query

Register Skills, then ask for a bounded set of relevant candidates:

After creating `manager` and `catalog`, use this in an async function:

```python
for skill in catalog:
    await manager.register_skill(skill)

matches = await manager.discover(
    "analyze PostgreSQL deadlocks",
    top_k=2,
)
print([skill.metadata.name for skill in matches])
```

The executable example registers a small in-memory catalog and uses the
default exact discovery provider:

```console
uv run python examples/03_dynamic_discovery.py
```

## Verified result

Output:

```text
['postgres-deadlocks']
```

Discovery returns candidates for the application to select and consume; it
does not invoke an agent or execute Skill instructions. For semantic matching
with application-selected embeddings, see the
[semantic discovery example](semantic-discovery.md).
