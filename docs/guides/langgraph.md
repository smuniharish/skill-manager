# Passing a SkillBundle to LangGraph

Build a bundle before invoking your graph, then pass it as ordinary
application state:

```python
from skill_manager import SkillBundle, SkillManager

# State is a TypedDict or model accepted by the application's graph.
bundle = await manager.build_bundle(selected_skills)
result = await graph.ainvoke({"bundle": bundle})
```

This is an integration excerpt, not a complete graph definition. Your graph
decides how to consume the bundle and owns model calls, tools, and execution.
Skill Manager resolves Skill-domain content and does not provide an agent
runtime. LangGraph instrumentation is optional, and LangSmith is not required.

The runnable
[LangGraph example](../examples/langgraph.md) passes a bundle through a
minimal state node and prints:

```text
['graph-consumer']
```

For a model-and-tool agent loop, see the
[LangChain `create_agent` example](../examples/langchain-create-agent.md).
