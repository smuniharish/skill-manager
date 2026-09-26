# Pass a SkillBundle through a LangGraph state

The minimal example treats `SkillBundle` as application graph state. The
graph consumes the selected Skill names; it does not invoke a model:

At the graph-invocation point:

```python
bundle = await manager.build_bundle([skill])
result = await graph.ainvoke({"bundle": bundle})
print([item.metadata.name for item in bundle.skills])
```

Run the complete graph example:

```console
uv run python examples/13_langgraph.py
```

## Verified result

Output:

```text
['graph-consumer']
```

Skill Manager owns Skill validation, lifecycle, discovery, and bundle
construction. LangGraph owns the application graph; agent execution and model
calls are separate concerns. This example does not require LangSmith. For an
agent loop, see the
[LangChain `create_agent` example](langchain-create-agent.md).
