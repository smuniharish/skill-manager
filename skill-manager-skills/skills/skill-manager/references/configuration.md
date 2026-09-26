# Configuration and extension decisions

Configure Skill Manager through `SkillManager(...)` and the immutable
`SkillManagerConfig`. Use the smallest extension surface that owns the
required behavior.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

## Policy configuration

`SkillManagerConfig` is the only Skill policy object:

| Option | Meaning |
| --- | --- |
| `allow_agent_skill_creation` | Permit agent-origin registration and structured generation. |
| `require_human_approval` | Keep new agent revisions pending until explicit approval. |

Do not duplicate these values as separate application flags passed through
another wrapper. Keep approval policy explicit and test both permitted and
denied paths where policy changes.

## Constructor decisions

| Need | Public injection |
| --- | --- |
| Canonical documents | `sources=[SkillSource, ...]` |
| Operational catalog | `registry=SkillRegistry` |
| Complete discovery replacement | `discovery_provider=DiscoveryProvider` |
| Retrieval stage | `retriever=SkillRetriever` |
| Final ranking stage | `reranker=SkillReranker` |
| Retrieval bound | `discovery_candidate_pool_size=...` |
| Extra Skill-domain validation | `validator=SkillValidator` |
| Approval/rejection persistence | `feedback_manager=FeedbackManager(...)` |
| Capability requirements | `mcp_runtime=MCPRuntime(...)` |
| External refresh | `refresh_engine=RefreshEngine(...)` |
| Skill lifecycle telemetry | `observability_sink=SkillObservabilitySink` |

An injected complete `discovery_provider` is mutually exclusive with
`retriever`, `reranker`, and a non-default candidate-pool size.

The
[constructor injection example](https://github.com/smuniharish/skill-manager/blob/master/examples/19_constructor_injection_matrix.py)
exercises every public injection point.

## Defaults

The zero-argument `SkillManager()` uses:

- no external sources;
- `InMemorySkillRegistry`;
- bounded lexical/exact discovery with deterministic score reranking;
- `DefaultSkillValidator`;
- default `FeedbackManager`;
- no MCP runtime or refresh engine;
- `NoOpSkillObservabilitySink`;
- agent creation enabled and human approval disabled.

These defaults need no database, model, hosted service, or LangSmith.

## Select extensions from evidence

- Add `FilesystemSkillSource` when canonical YAML lives on disk.
- Implement `SkillSource` for another document system.
- Implement `SkillRegistry` for durable or shared operational catalog state.
- Add semantic retrieval only when measured queries require meaning-based
  matching and the application can provide LangChain embeddings.
- Replace one discovery stage rather than the entire provider when only that
  stage differs.
- Add a validator for additional Skill-domain policy, not general application
  validation.
- Add telemetry through the provider-neutral sink and keep external
  observability setup application-owned.

Start with the closest runnable
[example](https://github.com/smuniharish/skill-manager/tree/master/examples)
and verify the decision against the
[documentation](https://skill-manager.readthedocs.io/en/latest/).
