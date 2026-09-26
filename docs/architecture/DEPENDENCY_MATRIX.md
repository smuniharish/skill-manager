# Dependency matrix

Metadata and public source APIs were checked against PyPI JSON and the
projects' public repositories on 2026-09-26. Compatibility is constrained to
Python 3.12 because `refresh-engine` and `mcp-capability-router` currently
declare `<3.13`.

| Package | Current release | Python compatibility | Purpose / responsibility owned | Public API used / integration | Failure behavior | Why mandatory; Skill Manager boundary |
|---|---:|---|---|---|---|---|
| `langchain` | 1.4.2 | `>=3.10,<4` | Application-facing models, runnables, agents and provider integrations | LangChain `Runnable` and `langchain_core.embeddings.Embeddings`; Skill Manager returns data, not a runnable agent | Provider/runnable exceptions remain application errors; Skill Manager wraps only failures at its own public boundaries | Required ecosystem target. Skill Manager owns Skills and does not create agents or execute instructions. |
| `langgraph` | 1.2.12 | `>=3.10` | Graph construction and execution/runtime | `StateGraph`, `START`, `END`; the application consumes `SkillBundle` in its own node | LangGraph exceptions remain LangGraph/application errors | Required ecosystem target. No execution, checkpoint, harness, or worker runtime is added here. |
| `xstructured` | 0.1.0 | `>=3.12` | Schema-guided extraction from LangChain `Runnable`s | `with_xstructured_output(runnable, schema)` and the resulting runnable's `ainvoke`; `XStructuredResult` exposes parsed output | Skill Manager translates failed extraction to `SkillValidationError` without registering a Skill | Required for agent-generated Skill extraction. Skill Manager supplies its Pydantic protocol model and still validates/governs the result. |
| `langgraph-xai` | 0.1.0 | `>=3.12` | LangGraph execution explainability, provenance links and instrumentation | `XAIRuntime(...).instrument(graph)`; `XAIConfig`, `FailureMode`; optional injection into `FeedbackManager(xai_runtime=...)` | Instrumentation raises `XAIInstrumentationError`; configured failure mode controls runtime capture behavior | Required for graph execution provenance integration. Skill-specific origin/revision facts remain fields on Skill, not a second graph-provenance platform. No LangSmith extra is installed or configured. |
| `contextsage` | 0.1.0 | `>=3.12` | Agent context preservation and summarization middleware | `IntelligentSummarizationMiddleware(model=..., trigger=..., keep=...)` passed to LangChain `create_agent` | Middleware reports/falls back according to its own recovery behavior; model or agent failures remain application failures | Required downstream integration. It is not used to prune SkillBundle requirements; essential Skill instructions and governance data must remain intact. |
| `refresh-engine` | 0.1.0 | `>=3.12,<3.13` | Discovery/change detection/planning/execution/scheduling of refresh operations | `RefreshEngine(source, operation)`, `refresh(mode, resource_ids, trigger)`, `AsyncScheduler`; `Resource`, `ResourceSnapshot`, `DiscoveryResult` | `RefreshResult` can represent `PARTIAL`/`FAILED`; `RefreshError`-family exceptions identify infrastructure failures | Required refresh infrastructure. Skill Manager re-reads sources and validates domain records after configured refresh work; it does not reimplement retries, state, overlap, or scheduling. |
| `mcp-capability-router` | 0.1.0 | `>=3.12,<3.13` | MCP capability indexing, discovery, retrieval, refresh, transport/runtime routing | `MCPRuntime.register_server` / `register_mcp_client`, `retrieve` / `query`, `execute`, `read_resource`, `get_prompt`, `refresh_server` | Runtime errors such as `CapabilityNotFoundError`, `RefreshError` and server errors propagate or are translated to `CapabilityResolutionError` at the Skill API | Required capability integration. Skill Manager only declares required capability names and resolves them; MCP routing remains in this package. |
| `feedback-manager` | 0.1.0 | `>=3.12,<3.15` | Feedback event model, persistence, routing, lifecycle and provenance correlation | `FeedbackManager.submit`, `query`, `get`, `resolve`, `reject`; `FeedbackTarget(type, id)` carries immutable Skill ID | `FeedbackManagerError` subclasses signal persistence, lifecycle, and configuration failures; approval/rejection must not change registry state if the event operation fails | Required governance feedback integration. Skill Manager owns authorization and Skill lifecycle decisions; the external manager owns feedback records and lifecycle. |
| Pydantic | 2.x | Compatible with Python 3.12 | Mature typed model validation and serialization | `BaseModel`, `ConfigDict(frozen=True)`, `Field`, `model_validate` | `ValidationError` is converted to a Skill validation error at the YAML boundary | Direct dependency for the Skill protocol; no custom schema validation framework. |
| PyYAML | 6.x | Compatible with Python 3.12 | YAML parsing | `yaml.safe_load` | Parser errors are converted to a Skill validation error; YAML is never executed | Direct dependency for the canonical YAML representation. |

All direct dependency lower/upper bounds are declared in `pyproject.toml`.
Optional provider credentials and hosted services are not required. No
LangSmith environment variables, identifiers, extras, or tracing requirement
are introduced.

## API verification notes

- The xstructured package exports `with_xstructured_output`,
  `XStructuredRunnable`, and `XStructuredResult`; the runnable implements
  asynchronous `ainvoke`.
- `MCPRuntime` exposes capability `retrieve` and `query`, and routing methods
  `execute`, `read_resource`, and `get_prompt`. It directly composes with
  `langchain-mcp-adapters` clients.
- `RefreshEngine.refresh` accepts refresh mode, resource IDs and trigger;
  `AsyncScheduler` accepts an async callback and an interval.
- `FeedbackManager.submit` accepts source, category, target, payload, and
  metadata. Its `reject(feedback_id, reason=...)` and `resolve(...)` methods
  operate on its own immutable event identifier, so Skill Manager must retain
  that identifier in Skill governance metadata and always address Skills by
  their `skill_id`.
- `XAIRuntime.instrument` instruments an already-compiled LangGraph and its
  constructor accepts application/tenant IDs. Tenant identifiers are optional
  application data; they are not LangSmith identifiers.
