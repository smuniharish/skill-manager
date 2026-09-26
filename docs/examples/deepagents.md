# Use a SkillBundle with Deep Agents

Deep Agents owns its planning and execution harness; Skill Manager supplies
the validated, resolved Skill content to the application. This example
passes bundle instructions as the agent's system prompt and does not use
Deep Agents' separate filesystem skill format.

Configure `EXPLABS_API_KEY` or `SKILL_MANAGER_LLM_API_KEY`,
`SKILL_MANAGER_LLM_BASE_URL`, and `SKILL_MANAGER_MODEL` in the process
environment or a secret manager.

## Run

Install the optional integration and run:

```console
uv sync --extra deepagents --extra openai-compatible
uv run --extra deepagents --extra openai-compatible python examples/23_deepagents.py
```

No LangSmith account or configuration is required. The integration excerpt
below assumes the application has already built the bundle and configured
its tools and model:

```python
agent = create_deep_agent(
    model=model,
    tools=[get_incident_record],
    system_prompt="\n".join(bundle.instructions),
)
result = await agent.ainvoke({"messages": messages})
```

## Verified result

The example constrains the agent to the supplied incident fixture and
asserts that the response includes its status and owner. One previously
verified hosted-model run reported:

```text
runtime=CompiledStateGraph
skills=['incident-evidence-review']
answer=INC-42 has exact status **monitoring** and owner **payments-platform**.
```

Model wording may vary. Skill instructions are not a sandbox; configure
agent tools, filesystem access, and other permissions at the application
boundary.
For a smaller agent integration, see
[LangChain `create_agent`](langchain-create-agent.md).
