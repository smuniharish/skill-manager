# Generating Skills with an application model

Use `generate_skill` when an application wants a LangChain `Runnable` to
produce a candidate matching the canonical `Skill` schema. The application
chooses the model and keeps provider credentials in its secret store or
process environment:

```console
pip install "skill-manager[openai-compatible]"
```

The following async excerpt adapts a chat model to the structured input
expected by generation:

```python
import os

from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from xstructured import schema_instructions

from skill_manager import Skill, SkillManager, SkillManagerConfig

manager = SkillManager(
    config=SkillManagerConfig(require_human_approval=True),
)
model = ChatOpenAI(
    model=os.environ["SKILL_MANAGER_MODEL"],
    base_url=os.environ["SKILL_MANAGER_LLM_BASE_URL"],
    api_key=os.environ["SKILL_MANAGER_LLM_API_KEY"],
    temperature=0,
)


def make_prompt(payload: dict[str, object]) -> str:
    return (
        f"{schema_instructions(Skill)}\n\n"
        f"Create a Skill for this request: {payload['request']}"
    )


generator = RunnableLambda(make_prompt) | model
candidate = await manager.generate_skill(
    generator,
    {"request": "Review SQL transaction safety."},
)
print(candidate.lifecycle.state.value)
```

The snippet is a complete generation flow inside an async function after the
three environment variables have been configured; no key value belongs in
source code or documentation. A model response is accepted only after
structured extraction and Skill validation. With approval required, a valid
candidate is registered as `PENDING_APPROVAL` and still needs an explicit
human decision.

The deterministic
[agent-generated Skill example](../examples/agent-generated-skill.md) runs
without a provider credential and prints `agent ACTIVE`. The
[feedback-informed regeneration example](../examples/feedback-informed-regeneration.md)
demonstrates review, correction, and re-approval with a real model.
