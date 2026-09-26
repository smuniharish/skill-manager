from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import yaml
from feedback_manager import FeedbackManager, FeedbackQuery, FeedbackStatus
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from langgraph_xai import XAIRuntime
from mcp_capability_router import MCPRuntime, Tool
from pydantic import BaseModel, Field
from refresh_engine import (
    DiscoveryResult,
    RefreshEngine,
    RefreshMode,
    Resource,
    ResourceSnapshot,
    TriggerSource,
)
from xstructured import EnvelopeSpec

from skill_manager import (
    CapabilityResolutionError,
    ExactDiscoveryProvider,
    FilesystemSkillSource,
    InMemorySkillRegistry,
    LexicalSkillRetriever,
    PipelineDiscoveryProvider,
    RetrievedSkill,
    Skill,
    SkillBundle,
    SkillCapability,
    SkillConflictError,
    SkillCreationDisabledError,
    SkillDependency,
    SkillDependencyCycleError,
    SkillDependencyError,
    SkillDiscoveryError,
    SkillGovernance,
    SkillLifecycleError,
    SkillLifecycleState,
    SkillManager,
    SkillManagerConfig,
    SkillMetadata,
    SkillNotFoundError,
    SkillObservabilityEvent,
    SkillOrigin,
    SkillProvenance,
    SkillReference,
    SkillRegistry,
    SkillReranker,
    SkillRetriever,
    SkillSource,
    SkillValidationError,
)
from skill_manager.errors import SkillSourceError
from skill_manager.resolution import resolve_dependencies
from skill_manager.validation import DefaultSkillValidator, parse_skill_yaml


def make_skill(
    name: str,
    *,
    version: str = "1.0.0",
    description: str | None = None,
    dependencies: tuple[SkillDependency, ...] = (),
    capabilities: tuple[SkillCapability, ...] = (),
    origin: SkillOrigin = SkillOrigin.HUMAN,
) -> Skill:
    return Skill(
        metadata=SkillMetadata(
            name=name,
            version=version,
            description=description or f"Instructions for {name}",
            tags=("test",),
        ),
        instructions=(f"Use {name} safely.",),
        dependencies=dependencies,
        capabilities=capabilities,
        provenance=SkillProvenance(origin=origin),
    )


class MemorySource(SkillSource):
    def __init__(self, source_id: str, documents: Mapping[str, str]) -> None:
        self._source_id = source_id
        self.documents = dict(documents)

    @property
    def source_id(self) -> str:
        return self._source_id

    async def load(self) -> Mapping[str, str]:
        return self.documents

    async def save(self, skill: Skill) -> None:
        self.documents[skill.skill_id] = yaml.safe_dump(
            skill.model_dump(mode="json"), sort_keys=True
        )

    async def delete(self, skill_id: str) -> None:
        self.documents.pop(skill_id, None)


class FailingSource(MemorySource):
    async def load(self) -> Mapping[str, str]:
        raise OSError("offline source")


class RefreshSource:
    async def discover(self) -> DiscoveryResult:
        async def resources() -> AsyncIterator[Resource]:
            yield Resource("skill-catalog")

        return DiscoveryResult(resources())

    async def snapshot(self, resource: Resource) -> ResourceSnapshot:
        return ResourceSnapshot(resource.resource_id, content={"revision": 1})


async def noop_refresh(
    resource: Resource | None,
    snapshot: ResourceSnapshot | None,
    action: Any,
    request: Any,
) -> None:
    return None


class GraphState(BaseModel):
    bundle: SkillBundle
    skill_ids: list[str] = Field(default_factory=list)


def test_manager_uses_default_or_explicit_policy_config() -> None:
    assert SkillManager().config == SkillManagerConfig()
    config = SkillManagerConfig(
        allow_agent_skill_creation=False,
        require_human_approval=True,
    )
    assert SkillManager(config=config).config is config


@pytest.mark.asyncio
async def test_manager_emits_skill_domain_observability_events() -> None:
    class RecordingSink:
        def __init__(self) -> None:
            self.events: list[SkillObservabilityEvent] = []

        async def emit(self, event: SkillObservabilityEvent) -> None:
            self.events.append(event)

    sink = RecordingSink()
    manager = SkillManager(observability_sink=sink)
    skill = make_skill("observable-skill")

    await manager.register_skill(skill)
    assert await manager.discover("observable skill", top_k=1) == [skill]
    await manager.build_bundle([skill])
    await manager.refresh()

    assert [event.name for event in sink.events] == [
        "skill.registered",
        "skill.discovery.completed",
        "skill.bundle.built",
        "skill.refresh.completed",
    ]
    assert sink.events[0].attributes["skill_id"] == skill.skill_id
    assert sink.events[1].attributes["result_count"] == 1
    assert manager.observability_errors == ()


@pytest.mark.asyncio
async def test_list_skills_returns_complete_and_filtered_catalog() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    human = make_skill("human-listing")
    pending = make_skill("pending-listing", origin=SkillOrigin.AGENT)
    approved_candidate = make_skill("approved-listing", origin=SkillOrigin.AGENT)
    rejected_candidate = make_skill("rejected-listing", origin=SkillOrigin.AGENT)
    await manager.register_skill(human)
    pending = await manager.register_skill(pending)
    approved_candidate = await manager.register_skill(approved_candidate)
    rejected_candidate = await manager.register_skill(rejected_candidate)
    approved = await manager.approve_skill(
        approved_candidate.skill_id,
        metadata={"reviewer": "catalog-reviewer", "reason": "Verified"},
    )
    rejected = await manager.reject_skill(
        rejected_candidate.skill_id,
        feedback="Missing rollback guidance",
        metadata={"reviewer": "catalog-reviewer"},
    )

    assert {skill.skill_id for skill in await manager.list_skills()} == {
        human.skill_id,
        pending.skill_id,
        approved.skill_id,
        rejected.skill_id,
    }
    assert await manager.list_skills(states={SkillLifecycleState.ACTIVE}) == (
        human,
        approved,
    )
    assert await manager.list_skills(states={SkillLifecycleState.PENDING_APPROVAL}) == (pending,)
    assert await manager.list_active_skills() == (human, approved)
    assert await manager.list_approved_skills() == (approved,)
    assert await manager.list_pending_skills() == (pending,)
    assert await manager.list_rejected_skills() == (rejected,)
    assert await manager.list_human_authored_skills() == (human,)
    assert await manager.list_agent_generated_skills() == (
        pending,
        approved,
        rejected,
    )
    assert await manager.list_agent_generated_skills(states={SkillLifecycleState.ACTIVE}) == (
        approved,
    )
    assert await manager.list_skills(
        states={SkillLifecycleState.REJECTED},
        origins={SkillOrigin.AGENT},
    ) == (rejected,)


def test_streamlit_dashboard_candidate_review_and_yaml_loading(tmp_path: Path) -> None:
    from examples._streamlit_dashboard import SkillDashboard  # type: ignore[missing-import]

    dashboard = SkillDashboard(tmp_path)
    try:
        approved_candidate = dashboard.create_candidate(
            name="visual-approval",
            version="1.0.0",
            description="Visually inspect approval behavior.",
            instructions=("Verify the candidate.",),
            tags=("ui",),
        )
        rejected_candidate = dashboard.create_candidate(
            name="visual-rejection",
            version="1.0.0",
            description="Visually inspect rejection behavior.",
            instructions=("Reject incomplete instructions.",),
            tags=("ui",),
        )

        approved = dashboard.approve(
            approved_candidate.skill_id,
            reviewer="developer",
            reason="Validated in the dashboard.",
        )
        rejected = dashboard.reject(
            rejected_candidate.skill_id,
            reviewer="developer",
            feedback="Add an escalation criterion.",
        )
        dashboard.refresh()

        assert approved.lifecycle.state is SkillLifecycleState.ACTIVE
        assert rejected.lifecycle.state is SkillLifecycleState.REJECTED
        assert dashboard.validate_yaml(dashboard.yaml(approved)) == approved
        assert len(dashboard.source_documents()) == 2
        assert len(dashboard.feedback_events()) == 2
        assert dashboard.manager.source_errors == {}
    finally:
        dashboard.close()

    reloaded = SkillDashboard(tmp_path)
    try:
        states = {skill.metadata.name: skill.lifecycle.state for skill in reloaded.skills()}
        assert states == {
            "visual-approval": SkillLifecycleState.ACTIVE,
            "visual-rejection": SkillLifecycleState.REJECTED,
        }
        assert len(reloaded.feedback_events()) == 2
        assert reloaded.manager.source_errors == {}
    finally:
        reloaded.close()


@pytest.mark.asyncio
async def test_observability_failure_is_recorded_without_replaying_domain_write() -> None:
    class FailingSink:
        async def emit(self, event: SkillObservabilityEvent) -> None:
            raise RuntimeError(f"telemetry unavailable for {event.name}")

    manager = SkillManager(observability_sink=FailingSink())
    skill = make_skill("observability-failure")

    assert await manager.register_skill(skill) == skill
    assert await manager.load(skill.skill_id) == skill
    assert len(manager.observability_errors) == 1
    assert "telemetry unavailable" in str(manager.observability_errors[0])


@pytest.mark.asyncio
async def test_yaml_round_trip_and_unsafe_inputs() -> None:
    skill = make_skill("postgres-analysis")
    document = yaml.safe_dump(skill.model_dump(mode="json"))
    loaded = parse_skill_yaml(document, DefaultSkillValidator())
    assert loaded.skill_id == skill.skill_id
    assert loaded.metadata.version == "1.0.0"

    with pytest.raises(SkillValidationError, match="malformed"):
        parse_skill_yaml("skill: [", DefaultSkillValidator())
    with pytest.raises(SkillValidationError, match="skill_id is required"):
        parse_skill_yaml("api_version: '1.0'\nkind: skill\n", DefaultSkillValidator())
    with pytest.raises(ValueError):
        make_skill("bad").model_copy(
            update={"resources": (SkillReference(name="x", path="../secret"),)}
        )


@pytest.mark.asyncio
async def test_filesystem_source_persists_and_removes_by_id(tmp_path: Path) -> None:
    source = FilesystemSkillSource(tmp_path)
    skill = make_skill("filesystem-skill")
    await source.save(skill)
    loaded = await source.load()
    assert len(loaded) == 1
    assert (
        parse_skill_yaml(next(iter(loaded.values())), DefaultSkillValidator()).skill_id
        == skill.skill_id
    )
    await source.delete(skill.skill_id)
    assert await source.load() == {}


@pytest.mark.asyncio
async def test_custom_registry_is_injected_into_manager() -> None:
    class RecordingRegistry(InMemorySkillRegistry):
        def __init__(self) -> None:
            super().__init__()
            self.put_ids: list[str] = []

        async def put(self, skill: Skill) -> None:
            self.put_ids.append(skill.skill_id)
            await super().put(skill)

    registry: SkillRegistry = RecordingRegistry()
    persisted = make_skill("persisted-registry")
    await registry.put(persisted)
    manager = SkillManager(registry=registry)
    skill = make_skill("custom-registry")

    assert await manager.load(persisted.skill_id) == persisted
    await manager.register_skill(skill)

    assert await registry.get(skill.skill_id) == skill
    assert await manager.load(skill.skill_id) == skill
    assert isinstance(registry, RecordingRegistry)
    assert registry.put_ids == [persisted.skill_id, skill.skill_id]


@pytest.mark.asyncio
async def test_failed_source_persistence_does_not_register_skill() -> None:
    class SaveFailureSource(MemorySource):
        async def save(self, skill: Skill) -> None:
            raise OSError("storage unavailable")

    source = SaveFailureSource("unavailable", {})
    manager = SkillManager(sources=[source])
    skill = make_skill("persist-failure")
    with pytest.raises(SkillSourceError, match="cannot persist"):
        await manager.register_skill(skill)
    with pytest.raises(SkillNotFoundError):
        await manager.load(skill.skill_id)


@pytest.mark.asyncio
async def test_multiple_sources_isolate_failures_and_invalid_documents() -> None:
    healthy_skill = make_skill("healthy-source")
    healthy = MemorySource(
        "database",
        {"valid.yaml": yaml.safe_dump(healthy_skill.model_dump(mode="json"))},
    )
    invalid = MemorySource("invalid", {"broken.yaml": "skill: ["})
    failed = FailingSource("remote", {})
    manager = SkillManager(sources=[healthy, invalid, failed])
    assert (await manager.load("healthy-source")).skill_id == healthy_skill.skill_id
    assert "remote" in manager.source_errors
    with pytest.raises(SkillSourceError):
        await manager.load("unknown-skill")


@pytest.mark.asyncio
async def test_refresh_removes_deleted_source_records_and_retains_healthy_catalog() -> None:
    skill = make_skill("source-removal")
    encoded = yaml.safe_dump(skill.model_dump(mode="json"))
    source = MemorySource("db", {skill.skill_id: encoded})
    manager = SkillManager(sources=[source])
    assert (await manager.load(skill.skill_id)).skill_id == skill.skill_id
    source.documents.clear()
    await manager.refresh()
    with pytest.raises(SkillNotFoundError):
        await manager.load(skill.skill_id)


@pytest.mark.asyncio
async def test_name_version_lookup_and_immutable_identity() -> None:
    manager = SkillManager()
    v1 = make_skill("versioned", version="1.0.0")
    v2 = make_skill("versioned", version="2.0.0")
    await manager.register_skill(v1)
    await manager.register_skill(v2)
    assert (await manager.load("versioned")).skill_id == v2.skill_id
    assert (await manager.load("versioned", version="1.0.0")).skill_id == v1.skill_id
    overwritten = v1.model_copy(update={"instructions": ("changed",)})
    with pytest.raises(SkillConflictError, match="immutable"):
        await manager.register_skill(overwritten)


@pytest.mark.asyncio
async def test_five_level_transitive_dependencies_and_cycle_path() -> None:
    catalog = [make_skill("f")]
    for child, parent in zip("edcba", "fedcb", strict=True):
        catalog.append(make_skill(child, dependencies=(SkillDependency(name=parent),)))
    ordered = resolve_dependencies((catalog[-1],), catalog)
    assert [skill.metadata.name for skill in ordered] == list("fedcba")

    a = make_skill("cycle-a", dependencies=(SkillDependency(name="cycle-b"),))
    b = make_skill("cycle-b", dependencies=(SkillDependency(name="cycle-a"),))
    with pytest.raises(SkillDependencyCycleError, match="cycle-a -> cycle-b -> cycle-a"):
        resolve_dependencies((a,), (a, b))


@pytest.mark.asyncio
async def test_missing_dependency_reports_path() -> None:
    skill = make_skill("requires-db", dependencies=(SkillDependency(name="database"),))
    with pytest.raises(SkillDependencyError, match="requires-db -> database"):
        resolve_dependencies((skill,), (skill,))


def test_dependency_resolver_backtracks_for_shared_version_constraints() -> None:
    version_two = make_skill("library", version="2.0.0")
    version_one = make_skill("library", version="1.5.0")
    first_root = make_skill(
        "first-consumer",
        dependencies=(SkillDependency(name="library", version=">=1"),),
    )
    second_root = make_skill(
        "second-consumer",
        dependencies=(SkillDependency(name="library", version="<2"),),
    )
    result = resolve_dependencies(
        (first_root, second_root),
        (version_one, version_two, first_root, second_root),
    )
    assert next(skill for skill in result if skill.metadata.name == "library") == version_one


@pytest.mark.asyncio
async def test_shared_capability_uses_mcp_router_once_and_builds_bundle() -> None:
    router = MCPRuntime()
    cap = Tool(
        capability_id="local:tool:postgres.query.read",
        server_id="local",
        name="postgres.query.read",
        description="Read PostgreSQL queries",
    )
    await router.registry.upsert_many([cap])
    manager = SkillManager(mcp_runtime=router)
    first = make_skill("first", capabilities=(SkillCapability(name=cap.name),))
    second = make_skill("second", capabilities=(SkillCapability(name=cap.name),))
    await manager.register_skill(first)
    await manager.register_skill(second)
    bundle = await manager.build_bundle((first, second))
    assert bundle.capabilities[cap.name] == (cap,)
    assert len(bundle.capabilities) == 1
    await router.close()


@pytest.mark.asyncio
async def test_capability_resolution_fails_explicitly_without_router() -> None:
    manager = SkillManager()
    skill = make_skill("needs-api", capabilities=(SkillCapability(name="api.read"),))
    await manager.register_skill(skill)
    with pytest.raises(CapabilityResolutionError, match="no MCPRuntime"):
        await manager.build_bundle((skill,))


@pytest.mark.asyncio
async def test_agent_creation_disabled_before_generator_execution() -> None:
    invoked = False

    def should_not_run(_: object) -> str:
        nonlocal invoked
        invoked = True
        raise AssertionError("generator must not run")

    manager = SkillManager(config=SkillManagerConfig(allow_agent_skill_creation=False))
    with pytest.raises(SkillCreationDisabledError):
        await manager.generate_skill(RunnableLambda(should_not_run), {"request": "test"})
    with pytest.raises(SkillCreationDisabledError):
        await manager.register_skill(make_skill("agent", origin=SkillOrigin.AGENT))
    assert not invoked
    assert await manager.list_pending_skills() == ()


@pytest.mark.asyncio
async def test_agent_without_approval_activates_and_human_needs_no_approval() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    human = await manager.register_skill(make_skill("human"))
    pending = await manager.register_skill(make_skill("agent", origin=SkillOrigin.AGENT))
    assert human.lifecycle.state is SkillLifecycleState.ACTIVE
    assert pending.lifecycle.state is SkillLifecycleState.PENDING_APPROVAL

    direct = SkillManager(config=SkillManagerConfig(require_human_approval=False))
    active = await direct.register_skill(make_skill("agent-active", origin=SkillOrigin.AGENT))
    assert active.lifecycle.state is SkillLifecycleState.ACTIVE


@pytest.mark.asyncio
async def test_approval_and_rejection_are_feedback_managed_by_skill_id() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    approved = await manager.register_skill(make_skill("needs-approval", origin=SkillOrigin.AGENT))
    active = await manager.approve_skill(
        approved.skill_id, metadata={"reviewer": "reviewer-1", "reason": "Verified"}
    )
    assert active.skill_id == approved.skill_id
    assert active.lifecycle.state is SkillLifecycleState.ACTIVE
    assert active.governance.approval_event_id

    rejected = await manager.register_skill(make_skill("needs-rejection", origin=SkillOrigin.AGENT))
    archived = await manager.reject_skill(
        rejected.skill_id,
        feedback="Missing transaction safety guidance",
        metadata={"reviewer": "reviewer-2", "severity": "high"},
    )
    assert archived.lifecycle.state is SkillLifecycleState.REJECTED
    assert archived.governance.rejection_event_id
    feedback_events = await manager._feedback.query(
        FeedbackQuery(
            category="rejection",
            target_type="skill",
            target_id=rejected.skill_id,
            status=FeedbackStatus.REJECTED,
        )
    )
    assert len(feedback_events) == 1
    assert feedback_events[0].payload["feedback"] == "Missing transaction safety guidance"
    assert (await manager.load(approved.skill_id)).skill_id == approved.skill_id
    with pytest.raises(SkillLifecycleError, match="rejected revisions"):
        await manager.remove_skill(archived.skill_id)


@pytest.mark.asyncio
async def test_concurrent_approval_cannot_duplicate_activation() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    pending = await manager.register_skill(make_skill("approve-once", origin=SkillOrigin.AGENT))
    outcomes = await asyncio.gather(
        *(
            manager.approve_skill(pending.skill_id, metadata={"reviewer": "reviewer"})
            for _ in range(2)
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(item, Skill) for item in outcomes) == 1
    assert sum(isinstance(item, SkillLifecycleError) for item in outcomes) == 1
    events = await manager._feedback.query(
        FeedbackQuery(
            category="approval",
            target_type="skill",
            target_id=pending.skill_id,
        )
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_source_cannot_bypass_agent_creation_or_approval_policy() -> None:
    agent = make_skill("external-agent-skill", origin=SkillOrigin.AGENT)
    forged = agent.model_copy(
        update={
            "governance": SkillGovernance(approval_event_id=str(uuid4())),
        }
    )
    source = MemorySource(
        "persisted",
        {agent.skill_id: yaml.safe_dump(forged.model_dump(mode="json"))},
    )
    approved_manager = SkillManager(
        sources=[source],
        config=SkillManagerConfig(require_human_approval=True),
    )
    assert (await approved_manager.list_pending_skills())[0].skill_id == agent.skill_id

    disabled_manager = SkillManager(
        sources=[source],
        config=SkillManagerConfig(allow_agent_skill_creation=False),
    )
    assert await disabled_manager.discover("external agent") == []
    assert next(iter(disabled_manager.source_errors.values())).startswith(
        "SkillCreationDisabledError:"
    )


@pytest.mark.asyncio
async def test_xstructured_generation_uses_rejection_feedback_and_revision_lineage() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    parent = await manager.register_skill(make_skill("retry-me", origin=SkillOrigin.AGENT))
    await manager.reject_skill(
        parent.skill_id,
        feedback="Include rollback guidance",
        metadata={"reviewer": "human"},
    )
    seen_input: dict[str, Any] = {}
    candidate = make_skill("retry-me", origin=SkillOrigin.AGENT).model_copy(
        update={
            "instructions": (
                "Keep the commit-boundary check.",
                "Include rollback guidance.",
            )
        }
    )

    def generator(input_value: dict[str, Any]) -> str:
        seen_input.update(input_value)
        return EnvelopeSpec().wrap(json.dumps(candidate.model_dump(mode="json")))

    revised = await manager.generate_skill(
        RunnableLambda(generator),
        {"request": "Revise the rejected database Skill"},
        parent_skill_id=parent.skill_id,
    )
    assert revised.lifecycle.state is SkillLifecycleState.PENDING_APPROVAL
    assert revised.skill_id != parent.skill_id
    assert revised.revision == parent.revision + 1
    assert revised.provenance.parent_skill_ids == (parent.skill_id,)
    feedback_context = seen_input["previous_skill_feedback"]
    assert feedback_context[0]["feedback"]["feedback"] == "Include rollback guidance"
    assert "Include rollback guidance." in revised.instructions
    assert await manager.list_rejected_skills() == (await manager.load(parent.skill_id),)


@pytest.mark.asyncio
async def test_malformed_xstructured_output_is_rejected_before_registration() -> None:
    manager = SkillManager()
    generator = RunnableLambda(lambda _: "The model did not return a Skill envelope.")
    with pytest.raises(SkillValidationError, match="xstructured could not extract"):
        await manager.generate_skill(generator, {"request": "Create a Skill"})
    assert await manager.discover("envelope") == []


@pytest.mark.asyncio
async def test_generate_skill_can_use_bounded_xstructured_repair() -> None:
    manager = SkillManager(config=SkillManagerConfig(require_human_approval=True))
    candidate = make_skill("repaired-generation", origin=SkillOrigin.AGENT)
    generator = RunnableLambda(lambda _: EnvelopeSpec().wrap('{"skill_id": "not-canonical"}'))
    repair = RunnableLambda(
        lambda _: EnvelopeSpec().wrap(json.dumps(candidate.model_dump(mode="json")))
    )

    generated = await manager.generate_skill(
        generator,
        "Create a repaired Skill",
        repair_generator=repair,
    )

    assert generated.metadata.name == "repaired-generation"
    assert generated.lifecycle.state is SkillLifecycleState.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_ten_thousand_skills_discovery_is_bounded() -> None:
    from skill_manager.discovery import ExactDiscoveryProvider

    skills = [
        make_skill(
            f"skill-{index:05}",
            version="1.0.0",
        )
        for index in range(10_000)
    ]
    skills[-1] = make_skill("postgres-deadlock-analysis")
    provider = ExactDiscoveryProvider()
    await provider.index(skills)
    found = await provider.discover("postgres deadlock", top_k=3)
    assert found
    assert found[0].metadata.name == "postgres-deadlock-analysis"
    assert len(found) <= 3


@pytest.mark.asyncio
async def test_custom_retriever_and_reranker_are_composed_and_bounded() -> None:
    class RecordingRetriever(SkillRetriever):
        def __init__(self) -> None:
            self.skills: tuple[Skill, ...] = ()
            self.limit: int | None = None

        async def index(self, skills: Sequence[Skill]) -> None:
            self.skills = tuple(skills)

        async def retrieve(
            self,
            query: str,
            *,
            limit: int,
            filters: Mapping[str, Any] | None = None,
        ) -> list[RetrievedSkill]:
            del query
            self.limit = limit
            candidates = [
                skill
                for skill in self.skills
                if not filters or filters.get("tag") in skill.metadata.tags
            ]
            return [
                RetrievedSkill(skill=skill, score=float(index))
                for index, skill in enumerate(candidates[:limit])
            ]

    class DescriptionLengthReranker(SkillReranker):
        async def rerank(
            self,
            query: str,
            candidates: Sequence[RetrievedSkill],
            *,
            top_k: int,
        ) -> list[Skill]:
            del query
            return sorted(
                (candidate.skill for candidate in candidates),
                key=lambda skill: (-len(skill.metadata.description), skill.skill_id),
            )[:top_k]

    retriever = RecordingRetriever()
    manager = SkillManager(
        retriever=retriever,
        reranker=DescriptionLengthReranker(),
        discovery_candidate_pool_size=3,
    )
    short = make_skill("short-result", description="short")
    long = make_skill(
        "long-result",
        description="a much longer preferred description",
    )
    excluded = make_skill("excluded-result", description="longest but excluded")
    short = short.model_copy(
        update={"metadata": short.metadata.model_copy(update={"tags": ("eligible",)})}
    )
    long = long.model_copy(
        update={"metadata": long.metadata.model_copy(update={"tags": ("eligible",)})}
    )
    await manager.register_skill(short)
    await manager.register_skill(long)
    await manager.register_skill(excluded)

    found = await manager.discover("custom", top_k=1, filters={"tag": "eligible"})

    assert found == [long]
    assert retriever.limit == 3


def test_manager_rejects_ambiguous_discovery_injection() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        SkillManager(
            discovery_provider=ExactDiscoveryProvider(),
            retriever=LexicalSkillRetriever(),
        )


@pytest.mark.asyncio
async def test_xai_runtime_is_delegated_through_feedback_manager() -> None:
    class RecordingXAIRuntime(XAIRuntime):
        def __init__(self) -> None:
            super().__init__()
            self.current_run_reads = 0

        @property
        def current_run(self) -> Any:
            self.current_run_reads += 1
            return super().current_run

    runtime = RecordingXAIRuntime()
    manager = SkillManager(
        config=SkillManagerConfig(require_human_approval=True),
        feedback_manager=FeedbackManager(xai_runtime=runtime),
    )
    try:
        pending = await manager.register_skill(make_skill("xai-feedback", origin=SkillOrigin.AGENT))
        await manager.approve_skill(pending.skill_id)
        assert runtime.current_run_reads == 1
    finally:
        await manager.close()
        await runtime.close()


@pytest.mark.asyncio
async def test_discovery_pipeline_rejects_invalid_reranker_output() -> None:
    class InjectingReranker(SkillReranker):
        def __init__(self, injected: Skill) -> None:
            self.injected = injected

        async def rerank(
            self,
            query: str,
            candidates: Sequence[RetrievedSkill],
            *,
            top_k: int,
        ) -> list[Skill]:
            del query, candidates, top_k
            return [self.injected]

    indexed = make_skill("indexed-candidate")
    injected = make_skill("injected-candidate")
    provider = PipelineDiscoveryProvider(
        reranker=InjectingReranker(injected),
        retriever=LexicalSkillRetriever(),
    )
    await provider.index((indexed,))

    with pytest.raises(SkillDiscoveryError, match="invalid candidate set"):
        await provider.discover("indexed", top_k=1)


@pytest.mark.asyncio
async def test_semantic_discovery_uses_langchain_embeddings_and_bounds_results() -> None:
    from skill_manager import SemanticDiscoveryProvider

    provider = SemanticDiscoveryProvider(DeterministicFakeEmbedding(size=16))
    skills = (
        make_skill(
            "database-review",
            description="Review database query performance",
        ),
        make_skill(
            "python-lint",
            description="Lint and format Python modules",
        ),
    )
    await provider.index(skills)
    results = await provider.discover("database performance", top_k=1)
    assert len(results) <= 1


@pytest.mark.asyncio
async def test_concurrent_discovery_resolution_and_langgraph_consumption() -> None:
    manager = SkillManager()
    skill = make_skill("graph-skill")
    await manager.register_skill(skill)
    found = await asyncio.gather(*(manager.discover("graph", top_k=1) for _ in range(20)))
    bundles = await asyncio.gather(*(manager.build_bundle((skill,)) for _ in range(20)))
    assert all(result[0].skill_id == skill.skill_id for result in found)
    assert all(bundle.skills[0].skill_id == skill.skill_id for bundle in bundles)

    builder = StateGraph(GraphState)
    builder.add_node(
        "consume",
        lambda state: {"skill_ids": [item.skill_id for item in state.bundle.skills]},
    )
    builder.add_edge(START, "consume")
    builder.add_edge("consume", END)
    graph = XAIRuntime(application_id="skill-manager-tests").instrument(builder.compile())
    result = await graph.ainvoke({"bundle": bundles[0]})
    assert result["skill_ids"] == [skill.skill_id]


@pytest.mark.asyncio
async def test_refresh_engine_integration_and_scheduler(tmp_path: Path) -> None:
    engine = RefreshEngine(RefreshSource(), noop_refresh)
    source = FilesystemSkillSource(tmp_path)
    manager = SkillManager(sources=[source], refresh_engine=engine)
    result = await manager.refresh(
        mode=RefreshMode.FULL,
        trigger=TriggerSource.MANUAL,
    )
    assert result is not None
    targeted = await manager.refresh(
        mode=RefreshMode.TARGETED,
        resource_ids=("skill-catalog",),
        trigger=TriggerSource.QUERY,
    )
    assert targeted is not None
    event_driven = await manager.refresh(
        mode=RefreshMode.TARGETED,
        resource_ids=("skill-catalog",),
        trigger=TriggerSource.EVENT,
    )
    assert event_driven is not None
    scheduler = await manager.schedule_refresh(3600)
    assert scheduler.state.value == "running"
    await manager.close()
    assert scheduler.state.value == "stopped"
    await engine.close()


@pytest.mark.asyncio
async def test_scheduled_refresh_uses_scheduled_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = SkillManager()
    triggers: asyncio.Queue[TriggerSource] = asyncio.Queue()

    async def record_refresh(*, trigger: TriggerSource) -> None:
        await triggers.put(trigger)

    monkeypatch.setattr(manager, "refresh", record_refresh)
    await manager.schedule_refresh(0.05)
    try:
        trigger = await asyncio.wait_for(triggers.get(), timeout=2)
    finally:
        await manager.close()
    assert trigger is TriggerSource.SCHEDULED


def test_model_rejects_secret_prompt_keys_and_credential_urls() -> None:
    with pytest.raises(ValueError, match="credentials"):
        SkillProvenance(source="https://user:password@example.com")
    skill = make_skill("secret-prompt").model_copy(
        update={"prompts": {"api_key": "do not serialize"}}
    )
    with pytest.raises(ValueError, match="credentials"):
        Skill.model_validate(skill.model_dump())
