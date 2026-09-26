---
name: skill-manager
description: Integrate, configure, extend, debug, or test the Skill Manager Python framework for governed YAML Skills in LangChain and LangGraph applications, including loading, validation, registration, discovery, dependencies, capabilities, bundles, approval, rejection, feedback-informed revisions, refresh, and observability. Use when an application needs reusable Skill lifecycle management without inventing an agent runtime.
---

# Skill Manager

Use this skill for the existing `skill-manager` Python package. Do not create
a second Skill protocol, agent runtime, orchestration layer, memory framework,
MCP router, feedback system, or model abstraction.

The package-level API is imported from `skill_manager`:

```python
from skill_manager import Skill, SkillManager, SkillManagerConfig, SkillMetadata
```

Skill Manager owns validated Skill-domain data and returns `SkillBundle`
objects. LangChain, LangGraph, or the application owns agent and model
execution.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

Read [`references/architecture.md`](references/architecture.md) before
changing ownership boundaries. Read
[`references/integration.md`](references/integration.md) before adding Skill
Manager to an application.

## Activate when

Use Skill Manager when an application needs to:

- define or consume canonical YAML Skills;
- load Skills from one or more sources and maintain an operational registry;
- validate, register, discover, version, or compose Skills;
- resolve Skill dependencies or required MCP capabilities;
- govern agent-generated Skills with human approval and rejection;
- regenerate an immutable revision using recorded rejection feedback;
- build a `SkillBundle` for a LangChain agent or LangGraph workflow;
- customize source, registry, validator, retrieval, reranking, or
  observability behavior;
- refresh Skill sources or inspect lifecycle and provenance catalog views;
- debug an existing Skill Manager integration.

Do not select it merely because an application uses prompts, tools, agents,
MCP, memory, or LangGraph without a governed Skill lifecycle.

## Required workflow

### Before changing an application

1. Inspect the installed/current Skill Manager version, dependency manifest,
   and existing `SkillManager` construction.
2. Inspect the application's current Skill documents, source and registry,
   discovery path, policy configuration, and bundle-consumption boundary.
3. Verify integration APIs against the public exports and published
   [documentation](https://skill-manager.readthedocs.io/en/latest/).
4. Start from the closest runnable
   [example](https://github.com/smuniharish/skill-manager/tree/master/examples).
5. Preserve the ownership boundary: Skill Manager prepares governed data;
   the host application executes it.

### Choose the correct lifecycle path

1. **Create a Skill in code:** construct `Skill` and `SkillMetadata`, then
   call `await manager.register_skill(skill)`.
2. **Load canonical YAML:** configure `FilesystemSkillSource` or implement
   `SkillSource`; let Skill Manager parse and validate documents.
3. **Discover candidates:** call `await manager.discover(...)`. Use the
   default bounded lexical discovery unless the workload demonstrates a need
   for embeddings or custom retrieval/reranking.
4. **Compose application data:** call `await manager.build_bundle(...)`.
   Pass the resulting bundle to the application's LangChain/LangGraph
   boundary; do not execute it inside Skill Manager.
5. **Generate an agent revision:** configure `SkillManagerConfig`, call
   `generate_skill` with a LangChain `Runnable`, and require human approval
   when application policy demands it.
6. **Approve or reject:** address a pending revision by immutable Skill ID.
   Rejected revisions remain auditable and cannot be activated.
7. **Revise after rejection:** call `generate_skill(...,
   parent_skill_id=rejected.skill_id)` from explicit application workflow.
   Feedback informs generation but never grants approval.
8. **Resolve capabilities:** inject the application's `MCPRuntime`; do not
   implement MCP discovery or routing in Skill Manager.
9. **Refresh sources:** inject `RefreshEngine` when external refresh behavior
   is required; Skill Manager ingests healthy source results.
10. **Observe lifecycle operations:** inject `SkillObservabilitySink`.
    Configure ecosystem telemetry on feedback-manager, refresh-engine,
    mcp-capability-router, and langgraph-xai directly.

## Integration rules

- Use YAML as the canonical serialized Skill representation. Markdown Agent
  Skills such as this file are developer guidance, not runtime Skills.
- Treat `SkillManagerConfig` as the single policy surface for
  `allow_agent_skill_creation` and `require_human_approval`.
- Use `SkillSource` for documents and `SkillRegistry` for validated
  operational catalog state. A database implementation can provide either or
  both contracts.
- Use `SkillRetriever` and `SkillReranker` for separate search stages, or
  `DiscoveryProvider` for the complete discovery workflow.
- Do not combine `discovery_provider` with direct retriever, reranker, or
  candidate-pool arguments.
- Build bundles only from active Skills. Resolve by immutable Skill ID where
  lifecycle precision matters.
- Keep credentials, full prompts, raw model output, and complete discovery
  queries out of observability attributes and feedback metadata.
- Preserve explicit failures. Do not suppress validation, source,
  dependency, capability, approval, or rejection errors.

## Prohibited shortcuts

Do **not**:

- represent runtime Skills as Markdown or execute YAML as code;
- invoke private modules when a public `skill_manager` export exists;
- mutate a Skill revision in place or reuse an ID for corrected content;
- expose pending or rejected revisions through discovery or bundle
  composition;
- treat every active Skill as human-approved;
- automatically regenerate or approve a Skill after feedback;
- duplicate feedback-manager, refresh-engine, mcp-capability-router,
  xstructured, ContextSage, or langgraph-xai behavior;
- add an agent loop, model-provider abstraction, memory, Harness, or
  long-running task runtime;
- require LangSmith;
- invent constructor parameters, environment variables, CLI commands, or
  host-specific adapters.

## Verification checklist

For an application change, add or update a focused test that proves the
requested behavior: source loading, validation failure, bounded discovery,
dependency order, capability resolution, lifecycle transition, feedback
lineage, bundle content, refresh result, or sanitized event emission. Exercise
the application's real sync/async boundary and run its formatter, linter,
type checker, and focused tests.

For changes to this skill, follow
[`../../validation/README.md`](../../validation/README.md). Consult the
authoritative [examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
and [documentation](https://skill-manager.readthedocs.io/en/latest/) rather
than expanding this file into a second manual.
