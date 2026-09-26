import asyncio
import json

from _common import make_skill
from langchain_core.runnables import RunnableLambda
from xstructured import EnvelopeSpec

from skill_manager import SkillManager


async def main() -> None:
    candidate = make_skill("generated-sql-review", "Review SQL for correctness and safety")
    generator = RunnableLambda(
        lambda _: EnvelopeSpec().wrap(json.dumps(candidate.model_dump(mode="json")))
    )
    manager = SkillManager()
    skill = await manager.generate_skill(generator, {"request": "Create a SQL review Skill"})
    print(skill.provenance.origin, skill.lifecycle.state)


if __name__ == "__main__":
    asyncio.run(main())
