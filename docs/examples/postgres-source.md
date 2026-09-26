# Persist Skills in PostgreSQL

The example implements the public `SkillSource` and `SkillRegistry`
extension points with PostgreSQL. Use it when documents and the operational
catalog must persist between manager instances.

## Public API excerpt

This async excerpt assumes application-provided `SkillSource` and
`SkillRegistry` adapters with open connections and a validated `skill`:

```python
from skill_manager import SkillManager

writer = SkillManager(sources=[source], registry=registry)
await writer.register_skill(skill, source_id=source.source_id)
source_reader = SkillManager(sources=[source])
loaded = await source_reader.load(skill.skill_id)
print(loaded.metadata.name)
```

The full example also verifies the catalog through a second registry
connection.

## Run

Install the optional driver:

```console
uv sync --extra postgres
```

For a disposable local database, provide `POSTGRES_PASSWORD` to Podman from
your shell or secret manager, then start PostgreSQL:

```powershell
podman run --detach --name skill-manager-postgres `
  --env POSTGRES_USER=skill_manager `
  --env POSTGRES_PASSWORD `
  --env POSTGRES_DB=skills `
  --publish 5432:5432 postgres:17-alpine
```

Configure `SKILL_MANAGER_POSTGRES_DSN` through your environment or secrets
manager; do not place a database URL or password in source control or
documentation. Then run:

```console
uv run --extra postgres python examples/17_postgres_source_and_registry.py
```

## Verified result

A previously verified PostgreSQL run loaded persisted YAML through a fresh
source-backed manager and the catalog entry through a fresh registry.
Its output had this variable-name shape:

```text
source loaded postgres-storage-<unique-suffix>
registry loaded postgres-storage-<unique-suffix>
registry lifecycle, conflict, and removal checks passed
```

Each run creates a uniquely named Skill and leaves the local tables and
container in place. Remove disposable infrastructure using your container
workflow when finished. The example is an integration pattern, not a
production database security or migration policy.
For the storage contract without a service, see
[custom sources](../guides/custom-source.md).
