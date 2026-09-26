# Loading Skills from YAML files

Use `FilesystemSkillSource` when canonical Skill documents should live as
YAML files in an application-managed directory:

Inside an async application function:

```python
from skill_manager import FilesystemSkillSource, SkillManager

source = FilesystemSkillSource("skills")
manager = SkillManager(sources=[source])
skill = await manager.load("postgres-analysis")
```

The source is one persistence option; the manager still validates documents
and applies Skill lifecycle and governance rules. Choose the catalog location,
filesystem permissions, backup policy, and deployment synchronization for
your application.

The
[filesystem example](../examples/filesystem-source.md) creates and loads one
canonical document. It is a runnable example and writes beneath `skills/`;
run it from an isolated checkout if you do not want to modify a local catalog.
For source adapters backed by another database, see the
[database source guide](database-source.md).
