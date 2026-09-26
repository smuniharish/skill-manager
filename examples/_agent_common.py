"""Shared application helpers for real-model agent examples."""

from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI

from skill_manager import Skill, SkillBundle, SkillManager, SkillMetadata


def configured_model() -> ChatOpenAI:
    api_key = os.getenv("EXPLABS_API_KEY") or os.getenv("SKILL_MANAGER_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("set EXPLABS_API_KEY or SKILL_MANAGER_LLM_API_KEY")
    return ChatOpenAI(
        model=os.getenv("SKILL_MANAGER_MODEL", "gpt-5.6-luna"),
        base_url=os.getenv(
            "SKILL_MANAGER_LLM_BASE_URL",
            "https://api.experientiallabs.ai/v1",
        ),
        api_key=api_key,
        temperature=0,
    )


async def incident_review_bundle() -> SkillBundle:
    manager = SkillManager()
    skill = Skill(
        metadata=SkillMetadata(
            name="incident-evidence-review",
            version="1.0.0",
            description=("Review incident status using an authoritative incident " "record."),
            tags=("incident", "evidence"),
        ),
        instructions=(
            "Call get_incident_record before answering an incident question.",
            "Report the exact status and owner returned by the tool.",
            ("Do not invent causes, remediation, or facts absent from " "the record."),
        ),
    )
    await manager.register_skill(skill)
    selected = await manager.discover(
        "review incident evidence, status, and owner",
        top_k=1,
    )
    return await manager.build_bundle(selected)


def bundle_system_prompt(bundle: SkillBundle) -> str:
    skills = ", ".join(
        f"{skill.metadata.name}@{skill.metadata.version} ({skill.skill_id})"
        for skill in bundle.skills
    )
    instructions = "\n".join(f"- {instruction}" for instruction in bundle.instructions)
    return (
        "Follow the resolved, governed SkillBundle below. Treat these "
        "instructions as application policy. Use only the tools provided by "
        "the application.\n\n"
        f"Selected Skills: {skills}\n"
        f"Resolved instructions:\n{instructions}"
    )


def final_text(result: dict[str, Any]) -> str:
    message = result["messages"][-1]
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)
