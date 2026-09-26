"""Local test MCP server for the live capability-router examples."""

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    "skill-manager-local-tools",
    host="127.0.0.1",
    port=8765,
    stateless_http=True,
)


@server.tool(name="github.pull_request.read")
def read_pull_request(number: int = 42) -> dict[str, object]:
    """Return a fixed, non-sensitive pull-request example."""
    return {
        "number": number,
        "title": "Document transaction safety checks",
        "state": "open",
    }


if __name__ == "__main__":
    server.run(transport="streamable-http")
