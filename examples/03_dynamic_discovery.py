import asyncio

from _common import make_skill

from skill_manager import SkillManager


async def main() -> None:
    manager = SkillManager()
    for skill in (
        make_skill("postgres-deadlocks", "Analyze PostgreSQL lock waits and deadlocks"),
        make_skill("python-formatting", "Format and lint Python source code"),
        make_skill("incident-summary", "Summarize production incidents"),
    ):
        await manager.register_skill(skill)
    matches = await manager.discover("analyze PostgreSQL deadlocks", top_k=2)
    print([skill.metadata.name for skill in matches])


if __name__ == "__main__":
    asyncio.run(main())
