import asyncio
import os

from _common import make_skill
from langchain_mcp_adapters.client import MultiServerMCPClient, StreamableHttpConnection
from langgraph.graph import END, START, StateGraph
from langgraph_xai import XAIRuntime
from mcp_capability_router import MCPRuntime
from pydantic import BaseModel, Field

from skill_manager import SkillBundle, SkillCapability, SkillManager


class State(BaseModel):
    bundle: SkillBundle
    skill_ids: list[str] = Field(default_factory=list)


async def main() -> None:
    server_name = os.environ.get("SKILL_MANAGER_MCP_SERVER", "tools")
    connection: StreamableHttpConnection = {
        "transport": "streamable_http",
        "url": os.environ["SKILL_MANAGER_MCP_URL"],
    }
    client = MultiServerMCPClient({server_name: connection})
    async with MCPRuntime() as runtime:
        await runtime.register_mcp_client(server_name, client)
        await runtime.refresh_server(server_name)
        manager = SkillManager(mcp_runtime=runtime)
        skill = make_skill("pull-request-analysis", "Analyze pull request changes").model_copy(
            update={
                "capabilities": (
                    SkillCapability(name=os.environ["SKILL_MANAGER_REQUIRED_CAPABILITY"]),
                )
            }
        )
        await manager.register_skill(skill)
        selected = await manager.discover("analyze a pull request", top_k=1)
        bundle = await manager.build_bundle(selected)

        builder = StateGraph(State)
        builder.add_node(
            "consume",
            lambda state: {"skill_ids": [item.skill_id for item in state.bundle.skills]},
        )
        builder.add_edge(START, "consume")
        builder.add_edge("consume", END)
        graph = XAIRuntime(application_id="skill-manager-e2e").instrument(builder.compile())
        result = await graph.ainvoke({"bundle": bundle})
        assert result["skill_ids"] == [item.skill_id for item in bundle.skills]
        print([item.metadata.name for item in bundle.skills])


if __name__ == "__main__":
    asyncio.run(main())
