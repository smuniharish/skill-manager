# Verified integration workflows

Import public Skill-domain symbols from `skill_manager`. Do not use private
submodules for normal application integration.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

## Install

Skill Manager requires Python 3.12:

```bash
pip install skill-manager
```

Install only the optional dependencies required by the application. Follow
the published
[documentation](https://skill-manager.readthedocs.io/en/latest/) and never
place API keys in source control.

## Register, discover, and build

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
        instructions=("Separate confirmed facts from hypotheses.",),
    )

    await manager.register_skill(skill)
    matches = await manager.discover("review an incident", top_k=1)
    bundle = await manager.build_bundle(matches)
    print(bundle.instructions)


asyncio.run(main())
```

`SkillBundle` is application data. Supply its instructions, capabilities,
resources, prompts, and provenance to the application boundary that needs
them.

## LangChain and LangGraph

Resolve the bundle before agent construction or graph invocation. The
[LangChain create_agent example](https://github.com/smuniharish/skill-manager/blob/master/examples/22_langchain_create_agent.py)
passes bundle instructions through `system_prompt`; the created agent is a
LangGraph compiled graph. The
[LangGraph example](https://github.com/smuniharish/skill-manager/blob/master/examples/13_langgraph.py)
passes the typed bundle through graph state.

Do not make Skill Manager execute tools, invoke a model, or own graph state.

## Deep Agents

Use the same bundle boundary with `create_deep_agent`, as shown in the
[Deep Agents example](https://github.com/smuniharish/skill-manager/blob/master/examples/23_deepagents.py).
Deep Agents' filesystem-oriented `skills=` feature is separate from Skill
Manager's governed YAML protocol. Do not map the runtime protocol to that
option or create duplicate Skill definitions.

## Agent generation and governance

Construct the manager with explicit policy and a feedback manager:

```python
from feedback_manager import FeedbackManager
from skill_manager import SkillManager, SkillManagerConfig

manager = SkillManager(
    config=SkillManagerConfig(
        allow_agent_skill_creation=True,
        require_human_approval=True,
    ),
    feedback_manager=FeedbackManager(),
)
```

Call `generate_skill` with a LangChain `Runnable`. A pending result is not
discoverable or bundle-ready. Approve or reject it by immutable Skill ID.
For explicit application-triggered correction, pass the rejected ID as
`parent_skill_id`; see the
[feedback-informed regeneration example](https://github.com/smuniharish/skill-manager/blob/master/examples/24_feedback_informed_regeneration.py).

## Supported example routes

Use the matching executable example as the starting point:

| Need | Authoritative example |
| --- | --- |
| Basic registration and bundle | [01_basic_skill.py](https://github.com/smuniharish/skill-manager/blob/master/examples/01_basic_skill.py) |
| Filesystem source | [02_filesystem_source.py](https://github.com/smuniharish/skill-manager/blob/master/examples/02_filesystem_source.py) |
| Semantic discovery | [04_semantic_discovery.py](https://github.com/smuniharish/skill-manager/blob/master/examples/04_semantic_discovery.py) |
| Dependencies | [07_transitive_dependencies.py](https://github.com/smuniharish/skill-manager/blob/master/examples/07_transitive_dependencies.py) |
| MCP capability | [09_mcp_capability.py](https://github.com/smuniharish/skill-manager/blob/master/examples/09_mcp_capability.py) |
| Approval and rejection | [11_approval.py](https://github.com/smuniharish/skill-manager/blob/master/examples/11_approval.py), [12_rejection_feedback.py](https://github.com/smuniharish/skill-manager/blob/master/examples/12_rejection_feedback.py) |
| PostgreSQL source and registry | [17_postgres_source_and_registry.py](https://github.com/smuniharish/skill-manager/blob/master/examples/17_postgres_source_and_registry.py) |
| Custom retrieval and reranking | [18_custom_retrieval_reranking.py](https://github.com/smuniharish/skill-manager/blob/master/examples/18_custom_retrieval_reranking.py) |
| Every constructor injection | [19_constructor_injection_matrix.py](https://github.com/smuniharish/skill-manager/blob/master/examples/19_constructor_injection_matrix.py) |
| Live services and telemetry | [20_live_all_parameters_grafana.py](https://github.com/smuniharish/skill-manager/blob/master/examples/20_live_all_parameters_grafana.py) |
| Human review UI | [21_streamlit_skill_lifecycle.py](https://github.com/smuniharish/skill-manager/blob/master/examples/21_streamlit_skill_lifecycle.py) |
| Catalog lifecycle views | [25_catalog_views.py](https://github.com/smuniharish/skill-manager/blob/master/examples/25_catalog_views.py) |

The full collection remains at
[Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples),
with workflow guidance in the
[Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/).
