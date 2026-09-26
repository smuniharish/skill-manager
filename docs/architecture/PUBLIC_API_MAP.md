# Public API map

Import Skill-domain symbols from `skill_manager`. Choose extension points
at the boundary you need to change, rather than replacing unrelated
infrastructure:

| Public symbol | Purpose |
|---|---|
| `SkillManager` | Async lifecycle facade with direct source, registry, retriever, reranker, validator, observability, and ecosystem-service injection. |
| `SkillManagerConfig` | Small immutable configuration for agent-generated Skill creation and approval policy. |
| `Skill`, `SkillMetadata`, `SkillDependency`, `SkillCapability`, `SkillReference`, `SkillProvenance`, `SkillLifecycle`, `SkillGovernance`, `SkillLifecycleState`, `SkillOrigin` | Typed Skill protocol/domain values and state/origin enums. |
| `SkillBundle` | Resolved, application-consumable collection with instructions, dependency order, capabilities, resources, prompts and provenance. |
| `FilesystemSkillSource`, `SkillSource` | Built-in document source and public async document-source contract. |
| `SkillRegistry` | Public ABC for the validated operational Skill catalog. |
| `InMemorySkillRegistry` | Concurrency-safe default registry used when no custom registry is injected. |
| `DiscoveryProvider` | Public ABC for indexing and bounded query discovery. |
| `ExactDiscoveryProvider`, `SemanticDiscoveryProvider` | Built-in lexical and optional embedding-based discovery. |
| `SkillRetriever`, `RetrievedSkill` | Public retrieval contract and scored candidate value. |
| `SkillReranker` | Public final-ordering contract for a bounded candidate set. |
| `PipelineDiscoveryProvider` | Composes custom retrieval and reranking stages. |
| `LexicalSkillRetriever`, `SemanticSkillRetriever`, `ScoreSkillReranker` | Built-in lexical/semantic retrieval and deterministic score reranking. |
| `DefaultSkillValidator`, `SkillValidator` | Default and customizable domain validation. |
| `SkillObservabilityEvent`, `SkillObservabilitySink`, `NoOpSkillObservabilitySink` | Provider-neutral Skill lifecycle telemetry contract and no-I/O default. |
| Domain exception types | Explicit input, source, discovery, dependency, capability and lifecycle failures. |

## Which extension point?

Use `SkillSource` for documents, `SkillRegistry` for the validated catalog,
`SkillRetriever`/`SkillReranker` for ranking stages, `DiscoveryProvider` for
the complete search workflow, `SkillValidator` for domain checks, and
`SkillObservabilitySink` for domain telemetry. `SkillManagerConfig` governs
agent-origin creation and approval. All are injected through the public
`SkillManager` constructor.

The external services are **not** Skill Manager extension contracts:
applications configure `MCPRuntime`, `RefreshEngine`, `FeedbackManager`,
LangChain runnables and LangGraph themselves. Consult the
[dependency matrix](DEPENDENCY_MATRIX.md) for integration APIs and verified
compatibility facts. No LangSmith setup is needed for the Skill domain.

## Catalog views

`SkillManager` exposes `list_skills(states=..., origins=...)` for combined
queries plus explicit `list_active_skills`, `list_approved_skills`,
`list_pending_skills`, `list_rejected_skills`,
`list_agent_generated_skills`, and `list_human_authored_skills` convenience
methods. Approved means active with a recorded approval event; it is not an
alias for every active Skill.

For example, `await manager.list_skills(states={SkillLifecycleState.ACTIVE})`
selects only active revisions; `await manager.load(skill_id)` retrieves a
specific revision even when it is rejected.
