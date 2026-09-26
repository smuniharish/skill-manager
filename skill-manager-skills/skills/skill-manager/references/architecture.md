# Skill Manager architecture for agents

Use this reference to decide what Skill Manager owns before changing an
application or proposing a new extension.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

## Ownership boundary

Skill Manager owns the Skill domain:

- canonical YAML and strongly typed models;
- immutable identity, revision, provenance, lifecycle, and governance;
- loading, validation, registration, and catalog access;
- bounded discovery and Skill-specific retrieval/reranking contracts;
- dependency and capability requirements;
- bundle composition;
- approval and rejection policy for agent-generated Skills;
- Skill-domain observability.

It delegates infrastructure to its owner:

| Responsibility | Owner |
| --- | --- |
| Agent and model execution | LangChain, LangGraph, provider, application |
| MCP transport, capability discovery, and routing | mcp-capability-router and the MCP ecosystem |
| Refresh execution, state, retries, and scheduling | refresh-engine |
| Structured model-output extraction | xstructured |
| Feedback records and persistence | feedback-manager |
| Context optimization | ContextSage |
| Graph execution provenance | langgraph-xai |
| Memory and long-running task execution | Application or dedicated infrastructure |

Do not create wrappers that merely rename these dependencies. Configure and
inject their public objects into `SkillManager` where supported.

## Lifecycle model

A Skill revision has an immutable `skill_id`, integer `revision`, metadata
version, provenance, lifecycle state, and governance record.

- Human-authored Skills are active by default.
- Agent-origin Skills are rejected when creation is disabled.
- With required human approval, agent-origin Skills enter
  `PENDING_APPROVAL`.
- Approval records feedback successfully before activating the revision.
- Rejection records feedback and retains the immutable rejected revision.
- A corrected revision receives a new Skill ID, increments `revision`, and
  records its rejected parent.

Feedback can inform a later generation request, but Skill Manager does not
autonomously invoke generation or approve content.

## Data flow

```text
SkillSource documents
        |
        v
parse -> validate -> governance -> SkillRegistry
                                  |
                                  v
                     discover active candidates
                                  |
                                  v
                dependencies + MCP requirements
                                  |
                                  v
                             SkillBundle
                                  |
                                  v
                 LangChain / LangGraph application
```

Sources and registries are separate extension points. The source owns
canonical documents; the registry owns validated operational catalog
behavior. The default registry is in-memory. Applications can provide
database-backed implementations without changing the Skill protocol.

## Canonical YAML versus Agent Skills

Skill Manager runtime Skills use its canonical YAML protocol. The
`skill-manager-skills/` directory follows the external Agent Skills
`SKILL.md` format only to teach coding agents how to use the package. Never
load this Markdown file into the runtime Skill catalog or make Markdown a
second runtime protocol.
