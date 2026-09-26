# Semantic discovery

Semantic discovery is opt-in. Supply a LangChain `Embeddings` implementation
to `SemanticDiscoveryProvider`; it embeds active Skills and ranks a query by
cosine similarity. The provider holds its vectors in memory and returns a
bounded `top_k` selection, not a dump of the catalog.

```python
from langchain_core.embeddings import FakeEmbeddings
from skill_manager import SemanticDiscoveryProvider, SkillManager

embeddings = FakeEmbeddings(size=8)
manager = SkillManager(discovery_provider=SemanticDiscoveryProvider(embeddings))
```

The snippet configures a local test embedding provider; register Skills and
call `await manager.discover("your query", top_k=3)` in an async context to
use it. For real relevance, choose an application-provided embedding model.
For persistent vectors or a larger catalog, implement `DiscoveryProvider`
or `SkillRetriever` instead. No hosted embedding service or credentials
are required by the default [lexical discovery](discovery.md).
