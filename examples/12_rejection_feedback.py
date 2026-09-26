import asyncio

from _common import make_skill

from skill_manager import SkillManager, SkillManagerConfig, SkillOrigin, SkillProvenance


async def main() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    pending = await manager.register_skill(
        make_skill("transaction-guidance", "Guide safe SQL transactions").model_copy(
            update={"provenance": SkillProvenance(origin=SkillOrigin.AGENT)}
        )
    )
    rejected = await manager.reject_skill(
        pending.skill_id,
        feedback="Include rollback and isolation-level guidance.",
        metadata={"reviewer": "developer", "severity": "high"},
    )
    retained = await manager.list_rejected_skills()
    print(f"state={rejected.lifecycle.state.value} retained_revisions={len(retained)}")
    print("Run examples/24_feedback_informed_regeneration.py for a corrected revision.")


if __name__ == "__main__":
    asyncio.run(main())
