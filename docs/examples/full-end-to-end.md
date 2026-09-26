# Discover a Skill, resolve a capability, and pass a bundle to LangGraph

This integration example exercises several application boundaries:

1. A local MCP server publishes a fixed, non-sensitive pull-request fixture.
2. `MCPRuntime` discovers the declared capability.
3. `SkillManager` discovers a matching Skill and builds a bundle.
4. A LangGraph node consumes the bundle as application state.

It does not create an LLM agent or execute model calls. Skill Manager handles
Skill-domain validation, lifecycle, discovery, and bundle construction; MCP
and LangGraph remain application integrations.

## Public API excerpt

After the application connects and refreshes `MCPRuntime`, this async
excerpt registers a Skill declaring the capability and builds the bundle
passed to its LangGraph node:

```python
from skill_manager import Skill, SkillCapability, SkillManager, SkillMetadata

manager = SkillManager(mcp_runtime=runtime)
skill = Skill(
    metadata=SkillMetadata(
        name="pull-request-analysis",
        version="1.0.0",
        description="Analyze pull request changes",
    ),
    instructions=("Review the pull-request facts.",),
    capabilities=(SkillCapability(name="github.pull_request.read"),),
)
await manager.register_skill(skill)
selected = await manager.discover("analyze a pull request", top_k=1)
bundle = await manager.build_bundle(selected)
result = await graph.ainvoke({"bundle": bundle})
```

`runtime` and `graph` are application-configured; the runnable example also
checks the node's returned Skill IDs.

## Run

Start the local MCP fixture in one terminal:

```console
uv run python examples/local_mcp_server.py
```

In a second PowerShell terminal, configure the local endpoint and run the
example:

```powershell
$env:SKILL_MANAGER_MCP_URL = "http://127.0.0.1:8765/mcp"
$env:SKILL_MANAGER_REQUIRED_CAPABILITY = "github.pull_request.read"
uv run --extra mcp python examples/14_full_end_to_end.py
```

The server name defaults to `tools`; override
`SKILL_MANAGER_MCP_SERVER` only when you use a different name. No provider
credential, hosted model, or LangSmith configuration is needed.

## Verified result

Output against the bundled local fixture:

```text
['pull-request-analysis']
```

For focused capability discovery, see the [MCP example](mcp.md); for bundle
consumption without an MCP server, see [LangGraph](langgraph.md).
