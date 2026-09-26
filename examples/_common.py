from skill_manager import (
    Skill,
    SkillDependency,
    SkillMetadata,
    SkillOrigin,
    SkillProvenance,
)


def make_skill(
    name: str,
    description: str,
    *dependencies: SkillDependency,
    skill_id: str | None = None,
    origin: SkillOrigin = SkillOrigin.HUMAN,
) -> Skill:
    values: dict[str, object] = {
        "metadata": SkillMetadata(name=name, version="1.0.0", description=description),
        "instructions": (f"Use the {name} capability safely.",),
        "dependencies": tuple(dependencies),
        "provenance": SkillProvenance(origin=origin),
    }
    if skill_id is not None:
        values["skill_id"] = skill_id
    return Skill.model_validate(values)
