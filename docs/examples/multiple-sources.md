# Load Skills from multiple sources

Use multiple sources when a catalog combines storage owned by different
application components. Inject the configured `SkillSource` implementations
into one manager:

In an async application workflow:

```python
manager = SkillManager(sources=[filesystem_source, database_source])
filesystem_skill = await manager.load("filesystem-skill")
database_skill = await manager.load("database-skill")
```

This is an excerpt; the source adapters are responsible for their own
persistence. Run the example, which combines YAML files and a standard-library
SQLite source:

```console
uv run python examples/05_multiple_sources.py
```

## Verified result

Output:

```text
filesystem-skill
database-skill
```

The example creates or updates local artifacts under `skills/`. Use an
isolated checkout if you do not want to change an existing catalog. For a
production database-backed source and registry, see the
[PostgreSQL example](postgres-source.md).
