# Share a capability across Skills

When multiple selected Skills require the same named capability, resolve it
once through the configured MCP runtime while building the bundle:

With a configured runtime and registered Skills:

```python
manager = SkillManager(mcp_runtime=mcp_runtime)
bundle = await manager.build_bundle([summary_skill, review_skill])
print(len(bundle.capabilities["github.pull_request.read"]))
```

This is an excerpt; both Skills declare the capability and `mcp_runtime` has
already been configured by the application. Run the deterministic local
registry example:

```console
uv run python examples/08_shared_capability.py
```

## Verified result

Output:

```text
github.pull_request.read: 1 shared capability resolved
```

Bundle construction resolves requirements; the consuming application remains
responsible for capability execution and authorization.
See the [local MCP example](mcp.md) for capability discovery.
