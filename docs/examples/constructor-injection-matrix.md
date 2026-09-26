# Constructor injection matrix

The runnable matrix overrides every supported `SkillManager` constructor
parameter and proves each override through observable behavior:

```console
uv run python examples/19_constructor_injection_matrix.py
```

## Verified result

Output from the deterministic injection example:

```text
{'direct_injections_verified': 11, 'complete_discovery_provider_verified': True, 'xai_delegated_through_feedback_manager': True, 'config_policy_override_verified': True}
```

## Verified parameters

| Parameter | Override | Observable proof |
|---|---|---|
| `sources` | Custom `SkillSource` | Skills load and save through the selected source. |
| `registry` | Custom `SkillRegistry` | The catalog reflects registered revisions. |
| `discovery_provider` | Custom `DiscoveryProvider` | Discovery returns the provider's candidates. |
| `retriever` | Custom `SkillRetriever` | Retrieval respects the configured candidate limit. |
| `reranker` | Custom `SkillReranker` | Application ordering determines discovery results. |
| `discovery_candidate_pool_size` | `7` | The custom retriever receives `limit=7`. |
| `validator` | Custom `SkillValidator` | Skill registration applies the supplied validator. |
| `config` | Explicit `SkillManagerConfig` values | Approval-required and creation-disabled policies are both exercised. |
| `feedback_manager` | `FeedbackManager(xai_runtime=...)` | Approval submits feedback and invokes XAI provenance resolution. |
| `mcp_runtime` | In-memory `MCPRuntime` | Bundle composition resolves the required capability. |
| `refresh_engine` | In-memory `RefreshEngine` | A full refresh returns a successful result. |
| `observability_sink` | Custom `SkillObservabilitySink` | Skill lifecycle events reach the sink. |

`discovery_provider` is a complete alternative to direct `retriever`,
`reranker`, and `discovery_candidate_pool_size` configuration. Combining them
is rejected because the manager could not unambiguously select an owner for
discovery.

XAI is configured through the public `feedback-manager` API:

```python
feedback = FeedbackManager(xai_runtime=xai_runtime)
manager = SkillManager(feedback_manager=feedback)
```

`FeedbackManager` owns the XAI provenance adapter. `SkillManager` therefore
does not duplicate an `xai_runtime` constructor parameter.
For focused extension guidance, see [custom discovery](../guides/custom-discovery.md).
