# Customizing Skill discovery

Start with the narrowest public extension that fits the application:

- Use a `SkillRetriever` for application-specific candidate retrieval.
- Use a `SkillReranker` to apply final business ordering to retrieved
  candidates.
- Inject those stages through `SkillManager(retriever=..., reranker=...)`.
- Use a complete `DiscoveryProvider` only when a single backend must own the
  entire discovery operation.

For example, after implementing the two stages:

```python
from skill_manager import SkillManager

manager = SkillManager(
    retriever=application_retriever,
    reranker=application_reranker,
    discovery_candidate_pool_size=20,
)
matches = await manager.discover("database operations", top_k=5)
```

This integration excerpt assumes the application has constructed both
implementations. Retrieval must honor `limit` and supplied filters; reranking
must return unique Skills from the candidate set and respect `top_k`.

The runnable
[custom retrieval and reranking example](../examples/custom-retrieval-reranking.md)
shows alias expansion and tag-based ordering. Its verified result is
`['postgres-operations', 'sql-review']`.
