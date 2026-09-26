import asyncio

from _common import make_skill

from skill_manager import SkillDependency, SkillManager


async def main() -> None:
    names = ("a", "b", "c", "d", "e", "f")
    manager = SkillManager()
    skills = {
        name: make_skill(
            f"skill-{name}",
            f"Example transitive dependency {name}",
            *([SkillDependency(name=f"skill-{names[index + 1]}")] if index < 5 else []),
        )
        for index, name in enumerate(names)
    }
    for skill in skills.values():
        await manager.register_skill(skill)
    bundle = await manager.build_bundle([skills["a"]])
    print([skill.metadata.name for skill in bundle.skills])


if __name__ == "__main__":
    asyncio.run(main())
