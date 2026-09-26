# Resolve transitive Skill dependencies

Select a top-level Skill and let bundle construction include its declared
dependencies:

After `manager` and `root_skill` have been initialized:

```python
bundle = await manager.build_bundle([root_skill])
print([skill.metadata.name for skill in bundle.skills])
```

Run the complete six-Skill chain example:

```console
uv run python examples/07_transitive_dependencies.py
```

## Verified result

Dependency-first output:

```text
['skill-f', 'skill-e', 'skill-d', 'skill-c', 'skill-b', 'skill-a']
```

The bundle preserves the dependency order expected by consumers. If a
required dependency is unavailable or the graph is invalid, bundle
construction raises a domain error rather than returning a partial success.
See [dependency concepts](../concepts/dependencies.md) for version
constraints and failure modes.
