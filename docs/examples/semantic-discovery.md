# Try semantic discovery

The runnable example uses LangChain's deterministic fake embeddings to show
how an embeddings implementation is injected:

## Public API excerpt

The runnable example registers two Skills before searching. In an async
function:

```python
from langchain_core.embeddings import DeterministicFakeEmbedding
from skill_manager import SemanticDiscoveryProvider, SkillManager

manager = SkillManager(
    discovery_provider=SemanticDiscoveryProvider(
        DeterministicFakeEmbedding(size=64)
    )
)
# Register the example Skills before searching.
matches = await manager.discover(
    "diagnose a transaction blocking another",
    top_k=2,
)
print([skill.metadata.name for skill in matches])
```

This is an excerpt, not a standalone program; see
[getting started](../getting-started.md) for registration.

## Run

```console
uv run python examples/04_semantic_discovery.py
```

## Verified result

Output from the deterministic fixture:

```text
['database-lock-analysis', 'python-formatting']
```

This output validates API wiring, not semantic relevance; deterministic fake
embeddings are not a relevance-quality test. Supply an application-selected
embeddings implementation for meaningful ranking. See the
[semantic discovery guide](../guides/semantic-discovery.md) or the
[Ollama embeddings example](ollama-embeddings.md) for a local model.
