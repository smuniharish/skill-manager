# Local model and ContextSage example

This application-level example registers a Skill, resolves a bundle, and
passes the Skill instructions to a LangChain agent backed by a real local
chat model. ContextSage is attached only at the consuming-agent boundary; it
is not a Skill Manager runtime or a substitute for Skill governance.

## Run with a local Ollama model

Start Ollama and pull a small model that supports chat completions:

```console
ollama serve
ollama pull qwen2.5:0.5b
uv sync --extra openai-compatible
uv run --extra openai-compatible python examples/15_local_llm_contextsage.py
```

The example defaults to `http://127.0.0.1:11434/v1` and `qwen2.5:0.5b`.
Override `SKILL_MANAGER_LLM_BASE_URL`, `SKILL_MANAGER_MODEL`, and
`SKILL_MANAGER_LLM_API_KEY` to use another OpenAI-compatible endpoint. Provide
credentials through the process environment or a secrets manager; never place
them in source files, command history, screenshots, or documentation.

## Verified result

The program prints the registered Skill's name and lifecycle, followed by
the model response. With `qwen2.5:0.5b`, one previously verified local run
produced:

```text
skill=sql-transaction-safety state=ACTIVE
- Check that a transaction has a clear rollback path.
- Review isolation assumptions and partial-failure handling.
```

Model wording can vary. The configured ContextSage trigger is intentionally
above this short exchange, so this example verifies middleware wiring, not a
summary transformation. Test summarization with a controlled long
conversation before relying on it for application-specific preservation
requirements.

The Skill bundle is supplied as the consuming agent's system prompt. An
application can pass the resolved instructions directly:

```python
bundle = await manager.build_bundle(selected_skills)
agent = create_agent(
    model=model,
    tools=application_tools,
    system_prompt="\n".join(bundle.instructions),
    middleware=[context_middleware],
)
```

This is an integration excerpt, not the complete example. Keep the bundle
small and ensure the consuming application preserves mandatory Skill
instructions and capability constraints when designing context policies.
ContextSage is optional middleware at the agent boundary; it is not a Skill
Manager dependency for execution and no LangSmith setup is required.

This smoke test does not use a hosted provider credential. During local
testing, `qwen2.5:0.5b` and `qwen2.5:1.5b` did not emit a complete xstructured
envelope for generated Skills; `generate_skill` rejected those malformed
candidates before registry mutation. Use a model that can follow the
xstructured envelope and Skill schema for agent generation. See the
[generation guide](../guides/agent-skill-generation.md).
