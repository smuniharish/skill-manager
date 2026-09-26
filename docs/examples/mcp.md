# Discover MCP capabilities

Use this example to confirm that an application-configured MCP server
advertises a required capability. It discovers capabilities without
invoking the tool.

## Public API excerpt

Given an application-connected `MCPRuntime`, this async excerpt uses the
router's public API:

```python
matches = await runtime.retrieve("read pull request details", limit=5)
for capability in matches:
    print(capability.capability_id, capability.name)
```

The runnable example connects an MCP client and refreshes the server before
retrieval.

## Run

Install the optional MCP client integration:

```console
uv sync --extra mcp
```

Start the bundled local fixture server in one terminal:

```console
uv run python examples/local_mcp_server.py
```

In a second PowerShell terminal, set its local endpoint and run capability
discovery:

```powershell
$env:SKILL_MANAGER_MCP_URL = "http://127.0.0.1:8765/mcp"
uv run --extra mcp python examples/09_mcp_capability.py
```

## Verified result

Against the bundled local fixture, capability discovery printed:

```text
tools:tool:github.pull_request.read github.pull_request.read
```

The router owns connection and capability discovery. Skill Manager can
resolve declared capability requirements while building a bundle, but this
example only discovers capabilities; it does not execute the tool. Replace
the fixture with an authorized application MCP server for real workloads.
To build a bundle requiring the discovered capability, see the
[local MCP and LangGraph example](full-end-to-end.md).
