import asyncio
import os

from langchain_mcp_adapters.client import MultiServerMCPClient, StreamableHttpConnection
from mcp_capability_router import MCPRuntime


async def main() -> None:
    server_name = os.environ.get("SKILL_MANAGER_MCP_SERVER", "tools")
    server_url = os.environ["SKILL_MANAGER_MCP_URL"]
    connection: StreamableHttpConnection = {
        "transport": "streamable_http",
        "url": server_url,
    }
    client = MultiServerMCPClient({server_name: connection})
    async with MCPRuntime() as runtime:
        await runtime.register_mcp_client(server_name, client)
        await runtime.refresh_server(server_name)
        matches = await runtime.retrieve("read pull request details", limit=5)
        for capability in matches:
            print(capability.capability_id, capability.name)


if __name__ == "__main__":
    asyncio.run(main())
