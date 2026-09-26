# Implementing a Skill source

Implement `SkillSource` when Skills must be loaded from application-owned
storage. `load` returns source locators mapped to YAML text; persistence
methods receive validated `Skill` values:

```python
from collections.abc import Mapping

from skill_manager import Skill, SkillSource


class ApplicationSource(SkillSource):
    @property
    def source_id(self) -> str:
        return "application-store"

    async def load(self) -> Mapping[str, str]:
        return await self.store.read_skill_documents()

    async def save(self, skill: Skill) -> None:
        await self.store.write_skill_document(skill.skill_id, skill)

    async def delete(self, skill_id: str) -> None:
        await self.store.delete_skill_document(skill_id)
```

This is a contract-shaped excerpt: `store` is an application-owned client
and is intentionally not defined here. Return YAML text rather than parsed
objects from `load`; keep serialization, authorization, transactions, and
secret handling appropriate to your backend. Inject one or more adapters as
`SkillManager(sources=[...])`.

See the runnable
[multiple-sources example](../examples/multiple-sources.md) and the
[PostgreSQL source and registry example](../examples/postgres-source.md).
