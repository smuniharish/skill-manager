# Architecture decisions

## ADR-001: YAML and a versioned typed protocol

YAML is the canonical human-authored representation. `api_version` denotes
the Skill protocol (independent of package version, Skill `metadata.version`,
identity, and integer revision). Input is parsed with `yaml.safe_load`, then
validated as a frozen Pydantic model and checked for domain invariants.

## ADR-002: Opaque immutable Skill identity

Each Skill revision has a generated `sk_` plus 26-character Crockford-base32
128-bit identifier. Name and semantic version are not governance identifiers.
A new revision receives a new ID and records its parent IDs; a rejected
revision remains queryable.

## ADR-003: Sources and registries have separate contracts

`SkillSource` loads YAML documents and saves/deletes validated Skill
revisions; `SkillRegistry` maintains the validated operational catalog for
lookup, discovery and lifecycle. The default `InMemorySkillRegistry` is
process-local, but either contract may have an application-provided durable
implementation. Loading one failing source must not discard valid records
from healthy sources. Registration validates and checks governance before
persisting an active revision.

## ADR-004: Discovery is bounded and replaceable

Exact filters and ranking are Skill-domain discovery. Retrieval yields a
bounded candidate set, reranking returns at most `top_k` active matches.
Applications may replace either stage or the complete provider. Semantic
retrieval accepts LangChain `Embeddings`; no model, vector database, API key,
or hosted service is required for default lexical discovery. Default score
tie-breaking uses Skill ID.

## ADR-005: Dependency resolution is deterministic and side-effect free

Dependencies use Skill name plus a PEP 440 version specifier. Resolution uses
the active catalog and returns topological dependency-first order. Missing,
conflicting, and cyclic requirements raise Skill-domain errors identifying
the dependency path. Capability lookup is a separate downstream operation.

## ADR-006: Governance gates every agent-origin write

`SkillManagerConfig(allow_agent_skill_creation=False)`
rejects before registry or source mutation. When approval is required, the
candidate is registered only as `PENDING_APPROVAL`, and is not persisted as
active. Approval/rejection is recorded in `feedback-manager` before lifecycle
transition. A failure in feedback persistence leaves the Skill lifecycle
unchanged. Human-origin Skills do not inherit the agent approval requirement.

## ADR-007: Skill composition is not execution

`SkillBundle` is immutable resolved data. Skill Manager never invokes its
instructions, tools, LangChain model, LangGraph graph, MCP operation, or
long-running task. The consuming application chooses execution and context
presentation.

## ADR-008: Integrate external lifecycle infrastructure directly

Use public APIs from `refresh-engine`, `mcp-capability-router`, `xstructured`,
`contextsage`, `langgraph-xai`, and `feedback-manager`, rather than parallel
Skill Manager implementations. Error translation is limited to preserving a
stable Skill-domain public error surface; external exception causes remain
chained.

## ADR-009: Keep input and telemetry safe

YAML is data, not executable instructions. Resource references are safe
relative paths; provenance URLs cannot contain credentials. Skill
observability events carry bounded domain metadata, not instructions,
prompts, discovery query text, or credentials. Applications choose where
telemetry is exported.

## Deferred choices

External APIs evolve; integrations are checked against declared dependency
constraints and the lockfile. Hosted embeddings, persistent sources or
registries, MCP transport configuration, model selection, and agent runtime
remain application decisions.
