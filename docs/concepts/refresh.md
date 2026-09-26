# Refresh

`await manager.refresh()` re-reads configured sources, updates Skill
discovery, and invalidates previously selected MCP capabilities. If an
application injects `refresh_engine=...`, Skill Manager first delegates the
resource refresh to the configured `refresh-engine.RefreshEngine`. The
external engine owns refresh operations and their status; Skill Manager
owns validating and ingesting Skills.

```python
import asyncio
from skill_manager import SkillManager

async def main():
    manager = SkillManager()
    result = await manager.refresh()
    print(result)

asyncio.run(main())
```

Output without an injected engine: `None`. With one, `refresh()` returns
its `RefreshResult`; failed engine refresh raises `SkillSourceError`.
Source failures are reported through `SkillSourceError` and
`manager.source_errors` while healthy source records remain available.
Applications requiring periodic refresh can call
`await manager.schedule_refresh(interval)` and stop the owned scheduler
with `await manager.close()`. Configure the external engine for targeted
resources or application-specific refresh work.
