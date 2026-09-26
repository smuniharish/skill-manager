import asyncio

from _common import make_skill

from skill_manager import SkillManager, SkillManagerConfig, SkillOrigin, SkillProvenance


async def main() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    pending = await manager.register_skill(
        make_skill("agent-sql-safety", "Review SQL safety").model_copy(
            update={"provenance": SkillProvenance(origin=SkillOrigin.AGENT, source="example")}
        )
    )
    await manager.approve_skill(
        pending.skill_id,
        metadata={"reviewer": "developer", "reason": "Verified"},
    )
    print((await manager.load(pending.skill_id)).lifecycle.state)


if __name__ == "__main__":
    asyncio.run(main())
