import asyncio

from _common import make_skill
from mcp_capability_router import MCPRuntime, Tool

from skill_manager import SkillCapability, SkillManager


async def main() -> None:
    runtime = MCPRuntime()
    capability = Tool(
        capability_id="local:tool:github.pull_request.read",
        server_id="local",
        name="github.pull_request.read",
        description="Read pull request details",
    )
    await runtime.registry.upsert_many([capability])
    manager = SkillManager(mcp_runtime=runtime)
    first = make_skill("pr-summary", "Summarize pull requests").model_copy(
        update={"capabilities": (SkillCapability(name=capability.name),)}
    )
    second = make_skill("pr-review", "Review pull request changes").model_copy(
        update={"capabilities": (SkillCapability(name=capability.name),)}
    )
    await manager.register_skill(first)
    await manager.register_skill(second)
    bundle = await manager.build_bundle([first, second])
    print(
        f"{capability.name}: "
        f"{len(bundle.capabilities[capability.name])} shared capability resolved"
    )
    await runtime.close()


if __name__ == "__main__":
    asyncio.run(main())
