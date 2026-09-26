# Add application-specific retrieval and reranking

Use a custom retriever for domain synonyms or backend-specific retrieval and
a reranker for final application ordering. The complete runnable example
implements both public extension points:

```console
uv run python examples/18_custom_retrieval_reranking.py
```

It expands a database query to PostgreSQL/SQL candidates, then prioritizes
Skills tagged `production`.

## Verified result

Output from the deterministic example:

```text
['postgres-operations', 'sql-review']
```

After implementing `SkillRetriever` and `SkillReranker`, inject them through
the manager:

```python
manager = SkillManager(
    retriever=application_retriever,
    reranker=application_reranker,
    discovery_candidate_pool_size=10,
)
matches = await manager.discover("database review", top_k=2)
```

This is an integration excerpt; the application implementations are omitted.
The retriever must respect its candidate `limit` and filters. The reranker
must return unique Skills from the retrieved candidates and not exceed
`top_k`. For a complete-provider alternative, see the
[constructor injection matrix](constructor-injection-matrix.md).
