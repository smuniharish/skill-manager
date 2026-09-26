"""Query the Skill catalog by lifecycle state and provenance origin."""

from __future__ import annotations

import asyncio

from _common import make_skill

from skill_manager import (
    SkillLifecycleState,
    SkillManager,
    SkillManagerConfig,
    SkillOrigin,
)


async def main() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    human = await manager.register_skill(
        make_skill("human-authored", "A human-authored active Skill.")
    )
    approved_candidate = await manager.register_skill(
        make_skill(
            "approved-agent",
            "An approved agent-generated Skill.",
            origin=SkillOrigin.AGENT,
        )
    )
    rejected_candidate = await manager.register_skill(
        make_skill(
            "rejected-agent",
            "A rejected agent-generated Skill.",
            origin=SkillOrigin.AGENT,
        )
    )
    pending = await manager.register_skill(
        make_skill(
            "pending-agent",
            "A pending agent-generated Skill.",
            origin=SkillOrigin.AGENT,
        )
    )
    approved = await manager.approve_skill(
        approved_candidate.skill_id,
        metadata={"reviewer": "developer", "reason": "Verified"},
    )
    rejected = await manager.reject_skill(
        rejected_candidate.skill_id,
        feedback="Add failure recovery instructions.",
        metadata={"reviewer": "developer"},
    )

    assert await manager.list_active_skills() == (human, approved)
    assert await manager.list_approved_skills() == (approved,)
    assert await manager.list_pending_skills() == (pending,)
    assert await manager.list_rejected_skills() == (rejected,)
    assert await manager.list_human_authored_skills() == (human,)
    assert len(await manager.list_agent_generated_skills()) == 3
    assert await manager.list_agent_generated_skills(states={SkillLifecycleState.REJECTED}) == (
        rejected,
    )

    print("active=2 approved=1 pending=1 rejected=1 " "agent_generated=3 human_authored=1")


if __name__ == "__main__":
    asyncio.run(main())
