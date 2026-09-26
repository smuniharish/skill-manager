import asyncio
from pathlib import Path

from _common import make_skill

from skill_manager import FilesystemSkillSource, SkillManager


async def main() -> None:
    source = FilesystemSkillSource(Path("skills"))
    skill = make_skill(
        "filesystem-analysis",
        "Analyze a local Skill source",
        skill_id="sk_00000000000000000000000001",
    )
    await source.save(skill)
    loaded = await SkillManager(sources=[source]).load(skill.metadata.name)
    print(loaded.skill_id)


if __name__ == "__main__":
    asyncio.run(main())
