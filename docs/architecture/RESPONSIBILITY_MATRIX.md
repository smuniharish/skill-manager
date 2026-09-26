# Responsibility matrix

| Responsibility | Owner | Skill Manager behavior |
|---|---|---|
| Skill protocol, models, identity, version and revision | skill-manager | Owns and validates the YAML Skill domain. |
| Skill lifecycle and governance policy | skill-manager | Enforces agent creation and approval boundaries before registry/source writes. |
| Skill sources and registry | skill-manager | Defines separate source and validated-catalog extension points, provides an in-memory registry default, and permits application-managed persistence implementations. |
| Exact, filtered and semantic Skill discovery | skill-manager | Exposes bounded retrieval and reranking extension points with lexical, semantic, and deterministic score defaults; returns candidates, not the complete catalog. |
| Dependency resolution and composition | skill-manager | Resolves constraints deterministically and reports dependency paths/cycles. |
| Capability requirements | skill-manager | Represents requirements on Skill models. |
| Capability discovery, indexing, retrieval and routing | mcp-capability-router | Uses `MCPRuntime` directly. No capability provider/router is introduced. |
| MCP transports and LangChain MCP client adaptation | mcp-capability-router / MCP and LangChain ecosystem | Skill Manager configures or consumes the existing runtime; it does not implement transport. |
| Source refresh, refresh state, scheduling, retries and overlap | refresh-engine | Maps Skill source snapshots to `RefreshEngine`; refresh execution/state remain external. |
| Structured agent Skill extraction | xstructured | Uses `with_xstructured_output` with the Skill model. Validation and governance remain Skill Manager responsibilities. |
| Context optimization | contextsage | Integrates at the consuming agent boundary; never silently removes required bundle facts. |
| Graph execution provenance / explainability | langgraph-xai | Applications instrument their LangGraph; Skill IDs can be included as domain input/context. |
| Feedback records, persistence, routing and lifecycle | feedback-manager | Submits Skill-targeted approval/rejection feedback and retains event IDs. |
| Agent and model execution | LangGraph / LangChain / provider | Out of scope; Skill Manager does not execute Skill instructions. |
| Long-running execution / Harness | application / LangGraph | Out of scope. |
| Memory | application / dedicated memory component | Out of scope. |
| Self-improvement or automatic policy mutation | application | Out of scope. |

## How to choose a boundary

Use `SkillSource` for canonical documents and `SkillRegistry` for validated
operational catalog storage; a durable implementation may supply either or
both. Use `SkillRetriever` and `SkillReranker` for separate search stages,
or `DiscoveryProvider` to replace the full workflow. Use `SkillValidator`
for extra Skill-domain checks. These contracts do not replace MCP routing,
refresh infrastructure, feedback persistence, or LangGraph execution.
Feedback is contextual evidence, never permission to rewrite governance.
