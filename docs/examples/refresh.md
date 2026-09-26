# Refresh a configured source

Inject a `RefreshEngine` configured for your application, then request a
manual full refresh:

```python
result = await manager.refresh(
    mode=RefreshMode.FULL,
    trigger=TriggerSource.MANUAL,
)
print(result.status)
```

This excerpt assumes the refresh-engine types and an engine configured with
the application's resource source are already available. The runnable
example uses an in-memory source and does not require an external database or
service:

```console
uv run python examples/10_refresh.py
```

## Verified result

Output:

```text
success
```

Applications that schedule refreshes should explicitly own engine startup,
error reporting, and shutdown.
See [refresh operations](../guides/refresh.md) for scheduling and failure
handling.
