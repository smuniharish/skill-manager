# Using a database-backed Skill source

Skill Manager provides a filesystem source; a database adapter is application
owned. Implement the public `SkillSource` contract, then inject the adapter
the same way as any other source:

Inside an async application function:

```python
from skill_manager import SkillManager, SkillSource

database_source: SkillSource = application_database_source
manager = SkillManager(sources=[database_source])
skill = await manager.load("incident-review")
```

The adapter stores canonical Skill documents and exposes its own persistence
and transaction policy. Keep database credentials and connection management
in the application. For an implementation pattern, see the
[multiple-sources example](../examples/multiple-sources.md); for a
PostgreSQL-backed source and registry, see the
[PostgreSQL example](../examples/postgres-source.md).
