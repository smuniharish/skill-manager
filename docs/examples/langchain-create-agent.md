# Use a SkillBundle with LangChain `create_agent`

This service-dependent example demonstrates the application boundary:

1. `SkillManager` registers, discovers, and resolves a Skill.
2. The application passes the resolved bundle instructions to LangChain.
3. LangChain owns model calls, tools, and the agent loop.

Configure `EXPLABS_API_KEY` or `SKILL_MANAGER_LLM_API_KEY`,
`SKILL_MANAGER_LLM_BASE_URL`, and `SKILL_MANAGER_MODEL` in your environment
or secret manager.

## Run

Run with the optional model integration:

```console
uv run --extra openai-compatible python examples/22_langchain_create_agent.py
```

No LangSmith account or configuration is required. The application can pass
bundle content to its own system prompt; for example, inside an async
application that has already created the bundle and tools:

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=[get_incident_record],
    system_prompt="\n".join(bundle.instructions),
)
result = await agent.ainvoke({"messages": messages})
```

This is an integration excerpt, not a standalone program. The full example
also adds task-specific instructions and a fixture tool.

## Verified result

The previously verified hosted-model run returned the authoritative tool
values:

```text
runtime=CompiledStateGraph
skills=['incident-evidence-review']
answer=INC-42 has status **monitoring** and is owned by **payments-platform**.
```

Model wording can vary. The example asserts that the response includes both
the record's status and owner. A LangChain agent runtime does not change
Skill Manager's role: it resolves Skill-domain data but does not execute
agent turns.
For a more feature-rich application harness, see
[Deep Agents](deepagents.md).
