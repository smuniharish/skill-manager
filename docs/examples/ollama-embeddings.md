# Use local Ollama embeddings for semantic discovery

The application selects a LangChain `OllamaEmbeddings` instance and injects
it into the semantic provider:

This integration excerpt assumes Skills have already been registered:

```python
from langchain_ollama import OllamaEmbeddings
from skill_manager import SemanticDiscoveryProvider, SkillManager

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://127.0.0.1:11434",
)
manager = SkillManager(
    discovery_provider=SemanticDiscoveryProvider(embeddings),
)
matches = await manager.discover(
    "Why does one database transaction block another?",
    top_k=1,
)
```

Install the optional integration:

```console
uv sync --extra ollama-embeddings
```

In one terminal, start Ollama:

```console
ollama serve
```

In another terminal, pull the model and run the example:

```console
ollama pull nomic-embed-text
uv run --extra ollama-embeddings python examples/16_local_ollama_embeddings.py
```

## Verified result

The runnable example registers a small fixture catalog. On the previously
verified local setup, the observed top result was:

```text
['postgres-deadlock-analysis']
```

This is a local service-dependent result; ranking quality varies with the
embedding model and catalog. The semantic provider is process-local, not a
vector database. For a deterministic API-only demonstration, see the
[semantic discovery example](semantic-discovery.md).
