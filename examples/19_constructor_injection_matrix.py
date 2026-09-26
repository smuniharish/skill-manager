"""Exercise every SkillManager constructor injection with observable checks."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

import yaml
from _common import make_skill
from feedback_manager import FeedbackManager
from langgraph_xai import XAIRuntime
from mcp_capability_router import MCPRuntime, Tool
from refresh_engine import (
    DiscoveryResult,
    RefreshEngine,
    RefreshMode,
    Resource,
    ResourceSnapshot,
    TriggerSource,
)

from skill_manager import (
    ExactDiscoveryProvider,
    InMemorySkillRegistry,
    RetrievedSkill,
    Skill,
    SkillCapability,
    SkillLifecycleState,
    SkillManager,
    SkillManagerConfig,
    SkillObservabilityEvent,
    SkillOrigin,
    SkillProvenance,
    SkillReranker,
    SkillRetriever,
    SkillSource,
)
from skill_manager.validation import DefaultSkillValidator


class RecordingSource(SkillSource):
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.load_calls = 0
        self.save_calls = 0

    @property
    def source_id(self) -> str:
        return "recording-source"

    async def load(self) -> Mapping[str, str]:
        self.load_calls += 1
        return self.documents

    async def save(self, skill: Skill) -> None:
        self.save_calls += 1
        self.documents[skill.skill_id] = yaml.safe_dump(skill.model_dump(mode="json"))

    async def delete(self, skill_id: str) -> None:
        self.documents.pop(skill_id, None)


class RecordingRegistry(InMemorySkillRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.put_calls = 0

    async def put(self, skill: Skill) -> None:
        self.put_calls += 1
        await super().put(skill)


class RecordingValidator(DefaultSkillValidator):
    def __init__(self) -> None:
        self.calls = 0

    def validate(self, skill: Skill) -> Skill:
        self.calls += 1
        return super().validate(skill)


class RecordingRetriever(SkillRetriever):
    def __init__(self) -> None:
        self.skills: tuple[Skill, ...] = ()
        self.requested_limit: int | None = None

    async def index(self, skills: Sequence[Skill]) -> None:
        self.skills = tuple(skills)

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedSkill]:
        del query, filters
        self.requested_limit = limit
        return [
            RetrievedSkill(skill=skill, score=float(len(self.skills) - index))
            for index, skill in enumerate(self.skills[:limit])
        ]


class RecordingReranker(SkillReranker):
    def __init__(self) -> None:
        self.calls = 0

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedSkill],
        *,
        top_k: int,
    ) -> list[Skill]:
        del query
        self.calls += 1
        return [candidate.skill for candidate in candidates[:top_k]]


class RecordingObservabilitySink:
    def __init__(self) -> None:
        self.events: list[SkillObservabilityEvent] = []

    async def emit(self, event: SkillObservabilityEvent) -> None:
        self.events.append(event)


class RecordingDiscoveryProvider(ExactDiscoveryProvider):
    def __init__(self) -> None:
        super().__init__()
        self.discover_calls = 0

    async def discover(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Skill]:
        self.discover_calls += 1
        return await super().discover(query, top_k=top_k, filters=filters)


class RecordingXAIRuntime(XAIRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.current_run_reads = 0

    @property
    def current_run(self) -> Any:
        self.current_run_reads += 1
        return super().current_run


class CatalogRefreshSource:
    async def discover(self) -> DiscoveryResult:
        async def resources() -> AsyncIterator[Resource]:
            yield Resource("skill-catalog")

        return DiscoveryResult(resources())

    async def snapshot(self, resource: Resource) -> ResourceSnapshot:
        return ResourceSnapshot(resource.resource_id, content={"revision": 1})


async def apply_refresh(
    resource: Resource | None,
    snapshot: ResourceSnapshot | None,
    action: Any,
    request: Any,
) -> None:
    del resource, snapshot, action, request


async def main() -> None:
    source = RecordingSource()
    registry = RecordingRegistry()
    retriever = RecordingRetriever()
    reranker = RecordingReranker()
    validator = RecordingValidator()
    observability = RecordingObservabilitySink()
    xai_runtime = RecordingXAIRuntime()
    feedback_manager = FeedbackManager(xai_runtime=xai_runtime)
    mcp_runtime = MCPRuntime()
    refresh_engine = RefreshEngine(CatalogRefreshSource(), apply_refresh)

    capability = Tool(
        capability_id="local:tool:catalog.read",
        server_id="local",
        name="catalog.read",
        description="Read the Skill catalog",
    )
    await mcp_runtime.registry.upsert_many([capability])

    manager = SkillManager(
        sources=[source],
        registry=registry,
        retriever=retriever,
        reranker=reranker,
        discovery_candidate_pool_size=7,
        validator=validator,
        config=SkillManagerConfig(
            allow_agent_skill_creation=True,
            require_human_approval=True,
        ),
        feedback_manager=feedback_manager,
        mcp_runtime=mcp_runtime,
        refresh_engine=refresh_engine,
        observability_sink=observability,
    )
    pending = await manager.register_skill(
        make_skill("injected-catalog", "Read the injected catalog").model_copy(
            update={
                "capabilities": (SkillCapability(name=capability.name),),
                "provenance": SkillProvenance(
                    origin=SkillOrigin.AGENT,
                    source="constructor-injection-example",
                ),
            }
        ),
        source_id=source.source_id,
    )
    assert pending.lifecycle.state is SkillLifecycleState.PENDING_APPROVAL
    approved = await manager.approve_skill(
        pending.skill_id,
        metadata={"reviewer": "example"},
    )
    matches = await manager.discover("injected catalog", top_k=1)
    bundle = await manager.build_bundle([approved])
    refresh_result = await manager.refresh(
        mode=RefreshMode.FULL,
        trigger=TriggerSource.MANUAL,
    )

    assert source.load_calls >= 1 and source.save_calls == 1
    assert registry.put_calls >= 1
    assert validator.calls >= 1
    assert retriever.requested_limit == 7
    assert reranker.calls == 1
    assert matches == [approved]
    assert capability.name in bundle.capabilities
    assert refresh_result is not None
    assert xai_runtime.current_run_reads == 1
    assert {event.name for event in observability.events} >= {
        "skill.registered",
        "skill.approved",
        "skill.discovery.completed",
        "skill.bundle.built",
        "skill.refresh.completed",
    }

    provider = RecordingDiscoveryProvider()
    provider_manager = SkillManager(discovery_provider=provider)
    provider_skill = make_skill("complete-provider", "Use a complete discovery provider")
    await provider_manager.register_skill(provider_skill)
    assert await provider_manager.discover("complete provider", top_k=1) == [provider_skill]
    assert provider.discover_calls == 1

    disabled_manager = SkillManager(
        config=SkillManagerConfig(
            allow_agent_skill_creation=False,
            require_human_approval=False,
        )
    )
    assert disabled_manager.config.allow_agent_skill_creation is False

    print(
        {
            "direct_injections_verified": 11,
            "complete_discovery_provider_verified": True,
            "xai_delegated_through_feedback_manager": True,
            "config_policy_override_verified": True,
        }
    )

    await manager.close()
    await provider_manager.close()
    await disabled_manager.close()
    await refresh_engine.close()
    await mcp_runtime.close()
    await xai_runtime.close()


if __name__ == "__main__":
    asyncio.run(main())
