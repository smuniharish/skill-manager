import asyncio

from _common import make_skill
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from skill_manager import SkillBundle, SkillManager


class State(BaseModel):
    bundle: SkillBundle
    skill_ids: list[str] = Field(default_factory=list)


async def main() -> None:
    manager = SkillManager()
    skill = make_skill("graph-consumer", "Skill consumed as application graph state")
    await manager.register_skill(skill)
    bundle = await manager.build_bundle([skill])
    builder = StateGraph(State)
    builder.add_node(
        "consume",
        lambda state: {"skill_ids": [item.skill_id for item in state.bundle.skills]},
    )
    builder.add_edge(START, "consume")
    builder.add_edge("consume", END)
    result = await builder.compile().ainvoke({"bundle": bundle})
    assert result["skill_ids"] == [item.skill_id for item in bundle.skills]
    print([item.metadata.name for item in bundle.skills])


if __name__ == "__main__":
    asyncio.run(main())
