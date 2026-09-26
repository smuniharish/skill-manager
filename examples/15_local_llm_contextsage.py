"""Example app: consume a resolved Skill through LangChain middleware."""

from __future__ import annotations

import asyncio
import os

from contextsage import IntelligentSummarizationMiddleware
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from skill_manager import Skill, SkillBundle, SkillManager, SkillMetadata


def _bundle_system_prompt(bundle: SkillBundle) -> str:
    instructions = "\n".join(f"- {instruction}" for instruction in bundle.instructions)
    return (
        "Use only the selected Skill instructions. Do not add general advice or "
        "technical claims not stated there. If asked for details not specified "
        "by the Skill, say that the Skill does not specify them. Do not claim "
        "to have tools that are not provided.\n\n"
        f"{instructions}"
    )


async def main() -> None:
    model = ChatOpenAI(
        model=os.getenv("SKILL_MANAGER_MODEL", "qwen2.5:0.5b"),
        base_url=os.getenv("SKILL_MANAGER_LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key=os.getenv("SKILL_MANAGER_LLM_API_KEY", "local-ollama"),
        temperature=0,
    )
    manager = SkillManager()
    skill = Skill(
        metadata=SkillMetadata(
            name="sql-transaction-safety",
            version="1.0.0",
            description="Review transaction safety and failure recovery.",
        ),
        instructions=(
            "Check that a transaction has a clear rollback path.",
            "Review isolation assumptions and partial-failure handling.",
            "Do not claim external tool access.",
        ),
    )
    await manager.register_skill(skill)
    bundle = await manager.build_bundle((skill,))

    context_middleware = IntelligentSummarizationMiddleware(
        model=model,
        trigger=("tokens", 10_000),
        keep=("messages", 4),
        policy="maximum_preservation",
        maximum_context_tokens=32_768,
        reserved_output_tokens=1_024,
        summarization_overhead_tokens=512,
    )
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=_bundle_system_prompt(bundle),
        middleware=[context_middleware],
    )
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": ("List only the checks explicitly stated by the selected Skill."),
                }
            ]
        }
    )
    print(f"skill={skill.metadata.name} state={skill.lifecycle.state.value}")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
