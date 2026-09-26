import asyncio
from collections.abc import AsyncIterator

from refresh_engine import (
    DiscoveryResult,
    RefreshEngine,
    RefreshMode,
    Resource,
    ResourceSnapshot,
    TriggerSource,
)

from skill_manager import SkillManager


class CatalogResources:
    async def discover(self) -> DiscoveryResult:
        async def resources() -> AsyncIterator[Resource]:
            yield Resource("skills")

        return DiscoveryResult(resources())

    async def snapshot(self, resource: Resource) -> ResourceSnapshot:
        return ResourceSnapshot(resource.resource_id, content={"catalog_version": 1})


async def apply_refresh(resource, snapshot, action, request) -> None:
    return None


async def main() -> None:
    engine = RefreshEngine(CatalogResources(), apply_refresh)
    manager = SkillManager(refresh_engine=engine)
    result = await manager.refresh(
        mode=RefreshMode.FULL,
        trigger=TriggerSource.MANUAL,
    )
    print(result.status if result is not None else "source-only refresh")
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
