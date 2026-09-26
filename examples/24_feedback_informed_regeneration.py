"""Regenerate a rejected agent Skill with human feedback and a real model."""

from __future__ import annotations

import asyncio
import os

from feedback_manager import (
    FeedbackCategory,
    FeedbackManager,
    FeedbackQuery,
    FeedbackStatus,
)
from langchain_openai import ChatOpenAI

from skill_manager import SkillManager, SkillManagerConfig


async def main() -> None:
    api_key = os.getenv("EXPLABS_API_KEY") or os.getenv("SKILL_MANAGER_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("set EXPLABS_API_KEY or SKILL_MANAGER_LLM_API_KEY")

    model = ChatOpenAI(
        model=os.getenv("SKILL_MANAGER_MODEL", "gpt-5.6-luna"),
        base_url=os.getenv(
            "SKILL_MANAGER_LLM_BASE_URL",
            "https://api.experientiallabs.ai/v1",
        ),
        api_key=api_key,
        temperature=0,
    )
    feedback_manager = FeedbackManager()
    manager = SkillManager(
        config=SkillManagerConfig(
            allow_agent_skill_creation=True,
            require_human_approval=True,
        ),
        feedback_manager=feedback_manager,
    )
    first = await manager.generate_skill(
        model,
        (
            "Create exactly one Skill named transaction-review version 1.0.0. "
            "Its only instruction must verify that the commit boundary is "
            "explicit."
        ),
        repair_generator=model,
    )
    rejected = await manager.reject_skill(
        first.skill_id,
        feedback=(
            "Add explicit rollback verification and isolation-level checks. "
            "Keep the commit-boundary check."
        ),
        metadata={"reviewer": "database-owner", "severity": "high"},
    )

    events = await feedback_manager.query(
        FeedbackQuery(
            category=FeedbackCategory.REJECTION,
            target_type="skill",
            target_id=rejected.skill_id,
            status=FeedbackStatus.REJECTED,
        )
    )
    revised = await manager.generate_skill(
        model,
        (
            "Regenerate transaction-review as version 1.1.0. Address every "
            "previous human rejection note explicitly while retaining the "
            "original valid instruction. Create a new canonical Skill ID."
        ),
        parent_skill_id=rejected.skill_id,
        repair_generator=model,
    )

    revised_text = " ".join(revised.instructions).lower()
    assert len(events) == 1
    assert events[0].payload["feedback"].startswith("Add explicit rollback verification")
    assert revised.skill_id != rejected.skill_id
    assert revised.revision == rejected.revision + 1
    assert revised.provenance.parent_skill_ids == (rejected.skill_id,)
    assert revised.lifecycle.state.value == "PENDING_APPROVAL"
    assert "rollback" in revised_text
    assert "isolation" in revised_text
    assert "commit" in revised_text

    approved = await manager.approve_skill(
        revised.skill_id,
        metadata={
            "reviewer": "database-owner",
            "reason": "All requested corrections are present.",
        },
    )
    assert approved.lifecycle.state.value == "ACTIVE"

    print(f"rejected={rejected.skill_id} state={rejected.lifecycle.state.value}")
    print(f"feedback={events[0].payload['feedback']}")
    print(
        f"revised={revised.skill_id} revision={revised.revision} "
        f"parent={revised.provenance.parent_skill_ids[0]}"
    )
    print(f"instructions={list(revised.instructions)}")
    print(f"final_state={approved.lifecycle.state.value}")


if __name__ == "__main__":
    asyncio.run(main())
