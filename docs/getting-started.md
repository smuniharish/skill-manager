# Getting started

Register a Skill, find it by description, and build a bundle before
integrating with an agent. This first run uses the default in-memory catalog:
no database, model, hosted service, credentials, or LangSmith configuration
is required.

## Install

Use CPython 3.12 and install the package:

```console
pip install skill-manager
```

If working from a checkout, `uv sync` installs the project's locked
dependencies; run the script with `uv run python first_skill.py`.

## Build your first bundle

Save this complete example as `first_skill.py`:

```python
import asyncio

from skill_manager import Skill, SkillManager, SkillMetadata


async def main() -> None:
    manager = SkillManager()
    skill = Skill(
        metadata=SkillMetadata(
            name="summarize-notes",
            version="1.0",
            description="Summarize meeting notes",
        ),
        instructions=("Summarize the notes in three bullets.",),
    )
    await manager.register_skill(skill)

    candidates = await manager.discover("summarize")
    bundle = await manager.build_bundle(candidates)
    print([item.metadata.name for item in candidates])
    print(bundle.instructions)


asyncio.run(main())
```

Run `python first_skill.py`. Verified output:

```text
['summarize-notes']
('Summarize the notes in three bullets.',)
```

The bundle contains resolved Skill-domain data; it does not execute its
instructions. Pass it to your application's agent or graph when appropriate.
The default catalog is process-local, so this example does not preserve
Skills across restarts.

## Move to a persistent catalog

Use `FilesystemSkillSource` for application-managed YAML documents:

```python
from skill_manager import FilesystemSkillSource, SkillManager

manager = SkillManager(sources=[FilesystemSkillSource("skills")])
```

This is a configuration excerpt: loading a named Skill requires an existing
document. See the [filesystem guide](guides/filesystem-source.md) for a
complete file-backed example and the [Skill protocol](concepts/skill-protocol.md)
for document fields. Applications needing a different backend can implement
the [source contract](guides/custom-source.md). A durable operational catalog
can be supplied separately through the [registry contract](concepts/registry.md).

## Next steps

- [Discover by meaning](guides/semantic-discovery.md) with application-selected
  embeddings, or use the default lexical discovery for no-model search.
- [Resolve dependencies and requirements](concepts/dependencies.md) before
  passing a bundle to a [LangGraph application](guides/langgraph.md).
- [Review agent-generated Skills](guides/approval-workflow.md) and inspect
  [catalog lifecycle views](examples/catalog-views.md).
- Consult the [API reference](reference/api.md) for public models, methods,
  and extension contracts.
