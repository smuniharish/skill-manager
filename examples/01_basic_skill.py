import asyncio

from _common import make_skill

from skill_manager import SkillManager


async def main() -> None:
    manager = SkillManager()
    skill = make_skill("postgres-analysis", "Analyze PostgreSQL query plans")
    await manager.register_skill(skill)
    bundle = await manager.build_bundle([skill])
    print(bundle.instructions)


if __name__ == "__main__":
    asyncio.run(main())
