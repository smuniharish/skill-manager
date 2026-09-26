# Capabilities

A Skill can declare required MCP capability names through `SkillCapability`.
When `build_bundle` resolves that Skill, Skill Manager asks an injected
`mcp_capability_router.MCPRuntime` for exact matches and puts selected
capabilities in `bundle.capabilities`. It does **not** execute tools or
route MCP operations; the application and MCP runtime own execution.

```python
from skill_manager import Skill, SkillCapability, SkillMetadata

skill = Skill(
    metadata=SkillMetadata(
        name="search-docs", version="1.0", description="Find documentation"
    ),
    instructions=("Look up relevant documentation.",),
    capabilities=(SkillCapability(name="search"),),
)
assert skill.capabilities[0].name == "search"
```

Configure `SkillManager(mcp_runtime=runtime)` before building a bundle
requiring capabilities. Without a configured runtime, or when a required
capability cannot be found, bundle construction raises
`CapabilityResolutionError`. After registering an MCP client, refresh its
server in the MCP runtime before resolving requirements; after later catalog
changes, call `await manager.refresh()` to invalidate selected capabilities.
No MCP server or hosted service is needed for Skills with no requirements.
