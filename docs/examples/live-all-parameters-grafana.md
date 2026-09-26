# Live integrations with Grafana and Tempo

This optional integration example exercises the supported
`SkillManager` extension points against live services: PostgreSQL, MCP,
feedback/XAI, refresh, a hosted model, and OpenTelemetry. It is an
application integration sample, not a core Skill Manager runtime.

## Public API excerpt

In this async application excerpt, `source`, `registry`, `feedback_manager`,
`mcp_runtime`, `refresh_engine`, and `sink` are application-configured
integrations. The full runnable example also connects the services,
approves the candidate, and sends the bundle to a graph and model.

```python
from skill_manager import SkillManager, SkillManagerConfig

manager = SkillManager(
    sources=[source],
    registry=registry,
    feedback_manager=feedback_manager,
    mcp_runtime=mcp_runtime,
    refresh_engine=refresh_engine,
    observability_sink=sink,
    config=SkillManagerConfig(
        allow_agent_skill_creation=True,
        require_human_approval=True,
    ),
)
await manager.register_skill(skill, source_id=source.source_id)
await manager.approve_skill(
    skill.skill_id,
    metadata={"reviewer": "integration-reviewer"},
)
selected = await manager.discover("live pull request analysis", top_k=1)
bundle = await manager.build_bundle(selected)
```

## Prepare services

Install the optional integrations:

```console
uv sync --extra mcp --extra openai-compatible --extra postgres --extra observability
```

Start Grafana's local LGTM stack:

```console
podman run --detach --name skill-manager-live-grafana `
  --publish 3000:3000 --publish 3200:3200 `
  --publish 4317:4317 --publish 4318:4318 `
  docker.io/grafana/otel-lgtm:latest
```

Provide `POSTGRES_PASSWORD` to Podman from a secret manager or process
environment before starting PostgreSQL:

```powershell
podman run --detach --name skill-manager-live-postgres `
  --env POSTGRES_USER=skillmanager `
  --env POSTGRES_PASSWORD `
  --env POSTGRES_DB=skillmanager `
  --publish 5432:5432 docker.io/library/postgres:17-alpine
```

Start the local MCP fixture in a separate terminal:

```console
uv run python examples/local_mcp_server.py
```

Configure `EXPLABS_API_KEY`, `SKILL_MANAGER_POSTGRES_DSN`, and
`SKILL_MANAGER_MCP_URL` in the process environment or secret manager. For
the bundled local MCP fixture, set the endpoint to
`http://127.0.0.1:8765/mcp`. The example defaults the trace endpoint to the
local Grafana collector at `http://127.0.0.1:4318/v1/traces`. No credential
values or database URLs belong in this guide.

Run from the project root:

```console
uv run --extra mcp --extra openai-compatible --extra postgres --extra observability python examples/20_live_all_parameters_grafana.py
```

## Verified result

The live run asserts that the Skill is persisted, the MCP capability is
resolved, feedback includes XAI execution provenance, the application
observability sink has no delivery errors, and an alternative complete
discovery provider finds the same revision. Generated Skill names and
execution identifiers vary. A previously verified run reported:

```text
skill=live-pr-analysis-<unique-suffix>
mcp_capability=github.pull_request.read
llm_response=Pull request #42, "Document transaction safety checks," is open.
grafana_service=skill-manager-live
```

Model wording may differ. The example does not require LangSmith; telemetry
is exported to the configured OpenTelemetry endpoint.

## Inspect traces

Open `http://127.0.0.1:3000/explore`, select Tempo, and query:

```traceql
{ resource.service.name = "skill-manager-live" }
```

The verified trace included events from the Skill lifecycle, refresh,
feedback, MCP operation, model call, and graph execution. Each integration
keeps its own event ownership while the application selects the telemetry
backend.
For a no-service injection exercise, see the
[constructor injection matrix](constructor-injection-matrix.md).
