# Discovery

`await manager.discover(query, top_k=5, filters=None)` returns at most
`top_k` active Skills, not the entire catalog or an executable agent. The
default lexical search considers Skill names, descriptions, tags,
instructions and capability names. Supported exact filters are `name`,
`version`, `tag`, and `capability`.

```python
import asyncio
from skill_manager import Skill, SkillManager, SkillMetadata

async def main():
    manager = SkillManager()
    await manager.register_skill(Skill(
        metadata=SkillMetadata(
            name="draft-report", version="1.0", description="Draft reports",
            tags=("writing",),
        ),
        instructions=("Draft a report.",),
    ))
    matches = await manager.discover("report", top_k=1, filters={"tag": "writing"})
    print([skill.metadata.name for skill in matches])

asyncio.run(main())
```

Output: `['draft-report']`.

For customized ranking, `SkillRetriever` returns bounded `RetrievedSkill`
candidates, then `SkillReranker` orders them. Inject either stage into
`SkillManager(retriever=..., reranker=...,
discovery_candidate_pool_size=50)`, compose a
`PipelineDiscoveryProvider`, or inject a complete `DiscoveryProvider`.
Do not combine `discovery_provider` with direct stage or candidate-pool
arguments. The pipeline rejects inactive, duplicate, out-of-filter, and
unknown reranker results; see [semantic discovery](semantic-discovery.md)
for embedding-based retrieval.
