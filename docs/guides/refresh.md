# Refreshing Skill sources

Use refresh when an application wants a configured
[`refresh-engine`](https://pypi.org/project/refresh-engine/) to refresh
upstream data and then make source updates available to Skill Manager:

```python
from refresh_engine import RefreshMode, TriggerSource

result = await manager.refresh(
    mode=RefreshMode.FULL,
    trigger=TriggerSource.MANUAL,
)
```

This excerpt assumes the application has already constructed a
`RefreshEngine` and injected it as `SkillManager(refresh_engine=engine)`.
Refresh sources, credentials, scheduling policy, and error handling remain
application configuration. Inspect the returned result and surface failures
according to the application's operational policy.

The
[refresh example](../examples/refresh.md) runs a deterministic in-memory
refresh and verifies the `success` result. If the application schedules
periodic refreshes, it should also own the engine's lifecycle and close it
during shutdown.
