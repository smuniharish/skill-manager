# Skill Manager

**Build trusted, discoverable Skill catalogs for LangChain and LangGraph applications.**

Skill Manager validates declarative Skills, manages their revisions and
approval state, discovers candidates, and resolves dependency-ordered
`SkillBundle` data. Your application owns the agent or graph that consumes
the bundle. The base workflow requires no hosted service or LangSmith setup.

## Start here

1. [Install and build your first bundle](getting-started.md) using a
   self-contained Skill and verified output.
2. [Understand Skills](concepts/skills.md), [identity and revisions](concepts/skill-id.md),
   and [bundle composition](concepts/skill-bundles.md).
3. Choose [filesystem storage](guides/filesystem-source.md) or an
   [application-owned source](guides/custom-source.md).

## Core workflows

| What you want to do | Guide | Runnable example |
| --- | --- | --- |
| Load Skill YAML | [Filesystem source](guides/filesystem-source.md) | [Files and validation](examples/filesystem-source.md) |
| Find relevant Skills | [Semantic discovery](guides/semantic-discovery.md) | [Deterministic embeddings](examples/semantic-discovery.md) |
| Create and review candidates | [Generation](guides/agent-skill-generation.md), [approval](guides/approval-workflow.md) | [Feedback-informed revisions](examples/feedback-informed-regeneration.md) |
| Resolve capabilities | [MCP capabilities](guides/mcp-capabilities.md) | [End-to-end local integration](examples/full-end-to-end.md) |

## Integrate with your application

Pass a resolved bundle to a [LangGraph node](guides/langgraph.md), a
[LangChain agent](examples/langchain-create-agent.md), or a
[Deep Agents application](examples/deepagents.md). For optional local model
and storage setups, see [Ollama embeddings](examples/ollama-embeddings.md),
[PostgreSQL source and registry](examples/postgres-source.md), and
[ContextSage integration](examples/local-llm-contextsage.md). Model providers
and their credentials are configured by the application, never by the Skill
definition.

## Extend and operate

- [Custom sources](guides/custom-source.md),
  [discovery](guides/custom-discovery.md), and
  [validation](guides/custom-validator.md) describe public extension contracts.
- [Catalog lifecycle views](examples/catalog-views.md),
  [refresh](guides/refresh.md), [performance](guides/performance.md), and
  the [Streamlit review console](examples/streamlit-skill-lifecycle.md)
  support operational workflows.
- [Architecture overview](architecture/overview.md) explains ownership and
  delegation; the [API reference](reference/api.md) lists public entry points.

Skills are untrusted declarative content. Skill Manager does not execute
instructions, manage an agent, implement MCP transport, or authorize users of
your application.
