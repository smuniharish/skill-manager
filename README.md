# skill-manager

**A governed Skill lifecycle for LangChain and LangGraph applications.**

Skill Manager turns reusable instructions into validated, discoverable, and
reviewable application assets. It gives teams one place to define Skills,
manage revisions, enforce approval policy, resolve dependencies and
capabilities, and produce a ready-to-use `SkillBundle`.

## Why Skill Manager?

Agent applications often load instructions directly from prompts, files, or
generated text. That approach becomes difficult to govern as the catalog
grows: identity is ambiguous, revisions are overwritten, dependencies are
implicit, generated content bypasses review, and every application invents
its own discovery logic.

Skill Manager provides a consistent Skill domain without replacing the agent
runtime:

- canonical YAML and strongly typed models
- immutable identity and revision lineage
- validated registration and bounded discovery
- dependency and capability resolution
- human approval and rejection feedback
- pluggable sources, registries, retrieval, and reranking
- resolved bundles for LangChain, LangGraph, and Deep Agents

## Install

Skill Manager requires Python 3.12.

```console
pip install skill-manager
```

## Quick start

```python
import asyncio

from skill_manager import Skill, SkillManager, SkillMetadata


async def main() -> None:
    manager = SkillManager()
    skill = Skill(
        metadata=SkillMetadata(
            name="incident-review",
            version="1.0.0",
            description="Review incidents using verified evidence.",
        ),
        instructions=(
            "Separate confirmed facts from hypotheses.",
            "Report unresolved risks explicitly.",
        ),
    )

    await manager.register_skill(skill)
    bundle = await manager.build_bundle([skill])
    print(bundle.instructions)


asyncio.run(main())
```

`SkillBundle` is validated application data. Pass it to the LangChain agent or
LangGraph workflow that owns execution.

## Scope

Skill Manager owns the Skill lifecycle. It does not execute agents, call
models, provide memory, implement MCP transport, or replace LangChain or
LangGraph. Those responsibilities remain with the application and their
respective libraries.

## Documentation

Read the [documentation](docs/index.md) for:

- [installation and first bundle](docs/getting-started.md)
- [Skill generation and governance](docs/guides/agent-skill-generation.md)
- [LangChain, LangGraph, and Deep Agents integrations](docs/index.md#integrate-with-your-application)
- [production-oriented runnable examples](docs/examples/basic.md)
- [public API reference](docs/reference/api.md)

Licensed under the [Apache License 2.0](LICENSE).
