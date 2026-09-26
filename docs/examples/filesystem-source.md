# Persist a Skill as YAML

The filesystem source stores canonical Skill YAML beneath the configured
directory. The runnable example saves one Skill, then loads it through a
manager using that source:

The load step in an async application looks like this:

```python
from skill_manager import FilesystemSkillSource, SkillManager

source = FilesystemSkillSource("skills")
manager = SkillManager(sources=[source])
skill = await manager.load("filesystem-analysis")
print(skill.skill_id)
```

Run the complete program from the project root:

```console
uv run python examples/02_filesystem_source.py
```

## Verified result

The persisted document loaded with the same immutable Skill ID:

```text
sk_00000000000000000000000001
```

The example uses a fixed valid immutable ID, so repeated runs update that
same YAML document. It writes beneath `skills/`; use a disposable checkout
when you do not want to modify a local catalog. Filesystem access policy and
backup/synchronization remain application responsibilities.
Next, [combine multiple sources](multiple-sources.md) or implement a
[custom source](../guides/custom-source.md).
