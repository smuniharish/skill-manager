# Semantic discovery

Use semantic discovery when a query should match a Skill by meaning rather
than by exact wording. Choose the embeddings implementation and its model in
your application, then give it to `SemanticDiscoveryProvider`:

```python
from langchain_core.embeddings import Embeddings

from skill_manager import SemanticDiscoveryProvider, SkillManager

embeddings: Embeddings = application_embeddings
manager = SkillManager(
    discovery_provider=SemanticDiscoveryProvider(embeddings),
)
matches = await manager.discover(
    "diagnose a transaction blocking another",
    top_k=3,
)
```

This is an excerpt for an async application that has already configured
`application_embeddings` and registered Skills. `top_k` bounds the returned
candidate set. The provider does not select, host, or require a remote model;
embedding cost, credentials, and service availability belong to the
application's embeddings integration.

For a dependency-free local API demonstration and its deterministic output,
see the [semantic discovery example](../examples/semantic-discovery.md).
For a real local embedding service, see the
[Ollama embeddings example](../examples/ollama-embeddings.md).
