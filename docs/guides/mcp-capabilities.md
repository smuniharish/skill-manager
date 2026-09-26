# Resolving MCP capabilities

Declare capability names on Skills and inject an application-configured
`MCPRuntime` when building bundles:

Inside an async application function, after selecting Skills:

```python
from skill_manager import SkillManager

# `mcp_runtime` has already been connected to the application's MCP servers.
manager = SkillManager(mcp_runtime=mcp_runtime)
bundle = await manager.build_bundle(selected_skills)
```

Each selected Skill's required capability names must resolve before bundle
construction succeeds. Skill Manager does not own MCP server discovery,
credentials, transport, tool execution, retries, or connection lifecycle;
those remain with the MCP runtime and the consuming application. A
`SkillBundle` describes resolved requirements but does not execute tools.

The
[MCP example](../examples/mcp.md) demonstrates local capability discovery.
The [shared capability example](../examples/shared-capability.md) verifies
that two Skills can refer to one resolved capability.
