"""Async application facade for Skill lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID

from feedback_manager import (
    FeedbackCategory,
    FeedbackManager,
    FeedbackQuery,
    FeedbackSource,
    FeedbackStatus,
    FeedbackTarget,
    FeedbackTargetType,
)
from langchain_core.runnables import Runnable
from mcp_capability_router import Capability, MCPRuntime
from refresh_engine import (
    AsyncScheduler,
    RefreshEngine,
    RefreshMode,
    RefreshResult,
    RefreshStatus,
    TriggerSource,
)

from skill_manager.config import SkillManagerConfig
from skill_manager.discovery import (
    DiscoveryProvider,
    ExactDiscoveryProvider,
    PipelineDiscoveryProvider,
    SkillReranker,
    SkillRetriever,
)
from skill_manager.errors import (
    CapabilityResolutionError,
    SkillApprovalError,
    SkillBundleError,
    SkillCreationDisabledError,
    SkillDiscoveryError,
    SkillGovernanceError,
    SkillLifecycleError,
    SkillNotFoundError,
    SkillRejectionError,
    SkillSourceError,
    SkillValidationError,
)
from skill_manager.models import (
    Skill,
    SkillBundle,
    SkillDependency,
    SkillGovernance,
    SkillLifecycle,
    SkillLifecycleState,
    SkillOrigin,
    SkillProvenance,
)
from skill_manager.observability import (
    NoOpSkillObservabilitySink,
    SkillObservabilityEvent,
    SkillObservabilitySink,
    SkillObservabilityValue,
)
from skill_manager.registry import InMemorySkillRegistry, SkillRegistry
from skill_manager.resolution import resolve_dependencies
from skill_manager.sources import SkillSource
from skill_manager.validation import DefaultSkillValidator, SkillValidator, parse_skill_yaml

logger = logging.getLogger(__name__)
_SECRET_METADATA_KEY = re.compile(
    r"(?:secret|password|token|credential|api[_-]?key|authorization)", re.IGNORECASE
)


def _validate_feedback_metadata(metadata: Mapping[str, Any]) -> None:
    for key, value in metadata.items():
        if _SECRET_METADATA_KEY.search(str(key)):
            raise SkillGovernanceError(
                "feedback metadata may not contain credential-like field names"
            )
        if isinstance(value, Mapping):
            _validate_feedback_metadata(value)
        elif isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, Mapping):
                    _validate_feedback_metadata(item)


class SkillManager:
    """Manage Skill lifecycle and return resolved data for LangChain/LangGraph apps.

    The manager owns Skill validation, registry state, discovery, composition and
    hard governance checks. It does not execute Skills or run agents.
    """

    def __init__(
        self,
        *,
        sources: Iterable[SkillSource] = (),
        registry: SkillRegistry | None = None,
        discovery_provider: DiscoveryProvider | None = None,
        retriever: SkillRetriever | None = None,
        reranker: SkillReranker | None = None,
        discovery_candidate_pool_size: int = 50,
        validator: SkillValidator | None = None,
        config: SkillManagerConfig | None = None,
        feedback_manager: FeedbackManager | None = None,
        mcp_runtime: MCPRuntime | None = None,
        refresh_engine: RefreshEngine | None = None,
        observability_sink: SkillObservabilitySink | None = None,
    ) -> None:
        """Create a manager with injected services and one policy config object."""
        self.config = config or SkillManagerConfig()
        self._sources = tuple(sources)
        source_ids = [source.source_id for source in self._sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Skill source IDs must be unique")
        self._source_by_id = {source.source_id: source for source in self._sources}
        self._source_for_skill: dict[str, str] = {}
        self._documents_by_source: dict[str, dict[str, str]] = {}
        self._registry = registry if registry is not None else InMemorySkillRegistry()
        if discovery_provider is not None and (
            retriever is not None or reranker is not None or discovery_candidate_pool_size != 50
        ):
            raise ValueError(
                "discovery_provider cannot be combined with retriever, reranker, "
                "or discovery_candidate_pool_size"
            )
        if discovery_provider is not None:
            self._discovery = discovery_provider
        elif retriever is not None:
            self._discovery = PipelineDiscoveryProvider(
                retriever,
                reranker=reranker,
                candidate_pool_size=discovery_candidate_pool_size,
            )
        else:
            self._discovery = ExactDiscoveryProvider(
                reranker=reranker,
                candidate_pool_size=discovery_candidate_pool_size,
            )
        self._validator = validator or DefaultSkillValidator()
        self._feedback = feedback_manager if feedback_manager is not None else FeedbackManager()
        self._mcp_runtime = mcp_runtime
        self._refresh_engine = refresh_engine
        self._observability = (
            observability_sink if observability_sink is not None else NoOpSkillObservabilitySink()
        )
        self._observability_errors: list[Exception] = []
        self._load_lock = asyncio.Lock()
        self._reindex_lock = asyncio.Lock()
        self._catalog_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._source_load_locks = {source.source_id: asyncio.Lock() for source in self._sources}
        self._lifecycle_locks: dict[str, asyncio.Lock] = {}
        self._capability_locks: dict[str, asyncio.Lock] = {}
        self._capability_cache: dict[str, Capability] = {}
        self._capability_epoch = 0
        self._loaded = False
        self._index_dirty = True
        self._catalog_version = 0
        self._source_errors: dict[str, str] = {}
        self._scheduler: AsyncScheduler | None = None
        self._scheduler_lock = asyncio.Lock()

    @property
    def source_errors(self) -> Mapping[str, str]:
        """Return the latest per-source load errors without suppressing failures."""
        return MappingProxyType(dict(self._source_errors))

    @property
    def observability_errors(self) -> tuple[Exception, ...]:
        """Return observability failures that did not interrupt Skill operations."""
        return tuple(self._observability_errors)

    async def load(self, name_or_skill_id: str, *, version: str | None = None) -> Skill:
        """Load a Skill by immutable ID or by name and optional semantic version."""
        await self._ensure_loaded()
        try:
            if name_or_skill_id.startswith("sk_"):
                return await self._registry.get(name_or_skill_id)
            return await self._registry.by_name(name_or_skill_id, version)
        except SkillNotFoundError:
            if self._source_errors:
                raise SkillSourceError(
                    "Skill sources could not all be read; see manager.source_errors"
                ) from None
            raise

    async def discover(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Skill]:
        """Return a bounded ranked set of active Skill candidates."""
        await self._ensure_loaded()
        await self._reindex_if_needed()
        matches = await self._discovery.discover(query, top_k=top_k, filters=filters)
        await self._emit_observability(
            "skill.discovery.completed",
            query_length=len(query),
            requested_top_k=top_k,
            result_count=len(matches),
            filtered=filters is not None,
        )
        return matches

    async def register_skill(
        self,
        skill: Skill,
        *,
        source_id: str | None = None,
    ) -> Skill:
        """Validate, enforce governance, register, and persist when policy allows."""
        if skill.provenance.origin is SkillOrigin.AGENT:
            self._require_agent_creation()
            if self.config.require_human_approval:
                skill = skill.model_copy(
                    update={
                        "lifecycle": SkillLifecycle(
                            state=SkillLifecycleState.PENDING_APPROVAL,
                            changed_at=datetime.now(UTC),
                        )
                    }
                )
            elif skill.lifecycle.state is not SkillLifecycleState.ACTIVE:
                raise SkillGovernanceError(
                    "agent Skill must be ACTIVE when human approval is disabled"
                )
        skill = self._validator.validate(skill)
        if (
            skill.lifecycle.state is SkillLifecycleState.ACTIVE
            and skill.governance.rejection_event_id
        ):
            raise SkillGovernanceError("a rejected Skill revision cannot be activated")
        selected_source = self._select_source(source_id)
        await self._write_skill(
            skill,
            selected_source,
            persist=skill.lifecycle.state is not SkillLifecycleState.PENDING_APPROVAL,
        )
        logger.info(
            "skill_registered", extra={"skill_id": skill.skill_id, "state": skill.lifecycle.state}
        )
        await self._emit_observability(
            "skill.registered",
            skill_id=skill.skill_id,
            skill_name=skill.metadata.name,
            skill_version=skill.metadata.version,
            lifecycle_state=skill.lifecycle.state.value,
            origin=skill.provenance.origin.value,
            persisted=selected_source is not None,
        )
        return skill

    async def generate_skill(
        self,
        generator: Runnable[Any, Any],
        input: Any,
        *,
        parent_skill_id: str | None = None,
        source_id: str | None = None,
        repair_generator: Runnable[Any, Any] | None = None,
    ) -> Skill:
        """Extract a Skill with xstructured, then validate and apply governance."""
        self._require_agent_creation()
        from xstructured import with_xstructured_output

        feedback_context: list[dict[str, Any]] = []
        parent: Skill | None = None
        if parent_skill_id is not None:
            parent = await self._registry.get(parent_skill_id)
            events = await self._feedback.query(
                FeedbackQuery(
                    category="rejection",
                    target_type="skill",
                    target_id=parent_skill_id,
                    status=FeedbackStatus.REJECTED,
                    limit=20,
                )
            )
            feedback_context = [
                {
                    "feedback": event.payload,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ]
        structured_input = input
        if isinstance(input, Mapping):
            structured_input = dict(input)
            if feedback_context:
                structured_input["previous_skill_feedback"] = feedback_context
        elif feedback_context:
            structured_input = (
                f"{input}\n\nPrevious rejected Skill feedback:\n" f"{feedback_context!r}"
            )
        try:
            result = await with_xstructured_output(
                generator,
                Skill,
                repair=repair_generator,
            ).ainvoke(structured_input)
        except Exception as error:
            raise SkillValidationError("xstructured could not extract a valid Skill") from error
        candidate = result.structured
        if not isinstance(candidate, Skill):
            raise SkillValidationError("xstructured returned a value outside the Skill protocol")
        provenance = candidate.provenance.model_copy(
            update={
                "origin": SkillOrigin.AGENT,
                "source": "xstructured",
                "generation_context": {
                    **candidate.provenance.generation_context,
                    **({"parent_skill_id": parent.skill_id} if parent is not None else {}),
                },
                "parent_skill_ids": (
                    (parent.skill_id,)
                    if parent is not None
                    else candidate.provenance.parent_skill_ids
                ),
            }
        )
        if parent is None and candidate.provenance.origin is not SkillOrigin.AGENT:
            provenance = provenance.model_copy(
                update={"parent_skill_ids": candidate.provenance.parent_skill_ids}
            )
        candidate = candidate.model_copy(
            update={
                "provenance": provenance,
                "revision": parent.revision + 1 if parent is not None else candidate.revision,
                "lifecycle": SkillLifecycle(
                    state=(
                        SkillLifecycleState.PENDING_APPROVAL
                        if self.config.require_human_approval
                        else SkillLifecycleState.ACTIVE
                    )
                ),
                "governance": SkillGovernance(),
            }
        )
        return await self.register_skill(candidate, source_id=source_id)

    async def approve_skill(
        self,
        skill_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> Skill:
        """Record human approval by immutable Skill ID and explicitly activate it."""
        lock = self._lifecycle_locks.setdefault(skill_id, asyncio.Lock())
        async with lock:
            return await self._approve_skill_locked(skill_id, metadata=metadata)

    async def _approve_skill_locked(
        self,
        skill_id: str,
        *,
        metadata: Mapping[str, Any] | None,
    ) -> Skill:
        skill = await self._registry.get(skill_id)
        if skill.lifecycle.state is not SkillLifecycleState.PENDING_APPROVAL:
            raise SkillLifecycleError("only a PENDING_APPROVAL Skill can be approved")
        if skill.provenance.origin is SkillOrigin.AGENT:
            self._require_agent_creation()
        details = dict(metadata or {})
        _validate_feedback_metadata(details)
        try:
            event = await self._feedback.submit(
                source=FeedbackSource.HUMAN,
                category=FeedbackCategory.APPROVAL,
                target=FeedbackTarget(type=FeedbackTargetType("skill"), id=skill_id),
                payload={"decision": "approved", "reason": details.get("reason")},
                metadata={"skill_revision": skill.revision, **details},
            )
            acknowledged = await self._feedback.acknowledge(event.feedback_id)
            handled = await self._feedback.mark_handled(acknowledged.feedback_id)
            resolved = await self._feedback.resolve(
                handled.feedback_id,
                resolution={"decision": "approved", "metadata": details},
            )
        except Exception as error:
            raise SkillApprovalError(f"approval feedback failed for Skill {skill_id!r}") from error
        governance = SkillGovernance(
            approval_event_id=str(resolved.feedback_id),
            reviewer=str(details["reviewer"]) if details.get("reviewer") is not None else None,
            reason=str(details["reason"]) if details.get("reason") is not None else None,
        )
        active = skill.model_copy(
            update={
                "lifecycle": SkillLifecycle(
                    state=SkillLifecycleState.ACTIVE,
                    changed_at=datetime.now(UTC),
                    reason=governance.reason,
                ),
                "governance": governance,
            }
        )
        try:
            source = self._source_by_id.get(self._source_for_skill.get(skill_id, ""))
            await self._replace_lifecycle(
                active,
                expected=SkillLifecycleState.PENDING_APPROVAL,
                source=source,
            )
        except Exception as error:
            raise SkillApprovalError(
                f"approval was recorded but Skill {skill_id!r} could not be activated"
            ) from error
        logger.info("skill_approved", extra={"skill_id": skill_id})
        await self._emit_observability(
            "skill.approved",
            skill_id=skill_id,
            skill_name=active.metadata.name,
            skill_version=active.metadata.version,
        )
        return active

    async def reject_skill(
        self,
        skill_id: str,
        *,
        feedback: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Skill:
        """Record rejection feedback by immutable ID and preserve the rejected revision."""
        lock = self._lifecycle_locks.setdefault(skill_id, asyncio.Lock())
        async with lock:
            return await self._reject_skill_locked(skill_id, feedback=feedback, metadata=metadata)

    async def _reject_skill_locked(
        self,
        skill_id: str,
        *,
        feedback: str,
        metadata: Mapping[str, Any] | None,
    ) -> Skill:
        skill = await self._registry.get(skill_id)
        if skill.lifecycle.state is not SkillLifecycleState.PENDING_APPROVAL:
            raise SkillLifecycleError("only a PENDING_APPROVAL Skill can be rejected")
        if not feedback.strip():
            raise SkillRejectionError("rejection feedback must not be empty")
        details = dict(metadata or {})
        _validate_feedback_metadata(details)
        try:
            event = await self._feedback.submit(
                source=FeedbackSource.HUMAN,
                category=FeedbackCategory.REJECTION,
                target=FeedbackTarget(type=FeedbackTargetType("skill"), id=skill_id),
                payload={"feedback": feedback},
                metadata={"skill_revision": skill.revision, **details},
            )
            acknowledged = await self._feedback.acknowledge(event.feedback_id)
            handled = await self._feedback.mark_handled(acknowledged.feedback_id)
            rejected_event = await self._feedback.reject(handled.feedback_id, reason=feedback)
        except Exception as error:
            raise SkillRejectionError(
                f"rejection feedback failed for Skill {skill_id!r}"
            ) from error
        governance = SkillGovernance(
            rejection_event_id=str(rejected_event.feedback_id),
            reviewer=str(details["reviewer"]) if details.get("reviewer") is not None else None,
            reason=feedback,
        )
        rejected = skill.model_copy(
            update={
                "lifecycle": SkillLifecycle(
                    state=SkillLifecycleState.REJECTED,
                    changed_at=datetime.now(UTC),
                    reason=feedback,
                ),
                "governance": governance,
            }
        )
        try:
            source = self._source_by_id.get(self._source_for_skill.get(skill_id, ""))
            await self._replace_lifecycle(
                rejected,
                expected=SkillLifecycleState.PENDING_APPROVAL,
                source=source,
            )
        except Exception as error:
            raise SkillRejectionError(
                f"rejection was recorded but Skill {skill_id!r} could not be archived"
            ) from error
        logger.info("skill_rejected", extra={"skill_id": skill_id})
        await self._emit_observability(
            "skill.rejected",
            skill_id=skill_id,
            skill_name=rejected.metadata.name,
            skill_version=rejected.metadata.version,
        )
        return rejected

    async def list_pending_skills(self) -> tuple[Skill, ...]:
        """Return every pending Skill revision."""
        return await self.list_skills(states={SkillLifecycleState.PENDING_APPROVAL})

    async def list_skills(
        self,
        *,
        states: set[SkillLifecycleState] | None = None,
        origins: set[SkillOrigin] | None = None,
    ) -> tuple[Skill, ...]:
        """Return registered revisions filtered by lifecycle state and origin."""
        await self._ensure_loaded()
        skills = await self._registry.all(states=states)
        if origins is None:
            return skills
        return tuple(skill for skill in skills if skill.provenance.origin in origins)

    async def list_active_skills(self) -> tuple[Skill, ...]:
        """Return every active Skill revision, regardless of origin."""
        return await self.list_skills(states={SkillLifecycleState.ACTIVE})

    async def list_approved_skills(self) -> tuple[Skill, ...]:
        """Return active revisions with a recorded human approval event."""
        active = await self.list_active_skills()
        return tuple(skill for skill in active if skill.governance.approval_event_id)

    async def list_agent_generated_skills(
        self,
        *,
        states: set[SkillLifecycleState] | None = None,
    ) -> tuple[Skill, ...]:
        """Return agent-generated revisions, optionally filtered by state."""
        return await self.list_skills(states=states, origins={SkillOrigin.AGENT})

    async def list_human_authored_skills(
        self,
        *,
        states: set[SkillLifecycleState] | None = None,
    ) -> tuple[Skill, ...]:
        """Return human-authored revisions, optionally filtered by state."""
        return await self.list_skills(states=states, origins={SkillOrigin.HUMAN})

    async def list_rejected_skills(self) -> tuple[Skill, ...]:
        """Return retained rejected revisions for audit and future revision work."""
        return await self.list_skills(states={SkillLifecycleState.REJECTED})

    async def remove_skill(self, skill_id: str) -> None:
        """Remove an active revision from its source and in-memory catalog."""
        skill = await self._registry.get(skill_id)
        if skill.lifecycle.state is SkillLifecycleState.REJECTED:
            raise SkillLifecycleError("rejected revisions are retained for auditability")
        source = self._source_by_id.get(self._source_for_skill.get(skill_id, ""))
        key_lock = self._catalog_locks.setdefault(
            (skill.metadata.name, skill.metadata.version), asyncio.Lock()
        )
        source_lock = self._source_load_locks[source.source_id] if source is not None else None
        if source_lock is not None:
            await source_lock.acquire()
        try:
            async with key_lock:
                if source is not None:
                    try:
                        await source.delete(skill_id)
                    except Exception as error:
                        raise SkillSourceError(
                            f"cannot delete Skill {skill_id!r} from source {source.source_id!r}"
                        ) from error
                await self._registry.remove(skill_id)
                self._source_for_skill.pop(skill_id, None)
                self._mark_index_dirty()
        finally:
            if source_lock is not None:
                source_lock.release()

    async def build_bundle(self, skills: Iterable[Skill | str]) -> SkillBundle:
        """Resolve transitive dependencies and required MCP capabilities into a bundle."""
        await self._ensure_loaded()
        roots: list[Skill] = []
        for item in skills:
            root = (
                await self.load(item) if isinstance(item, str) else await self.load(item.skill_id)
            )
            if root.lifecycle.state is not SkillLifecycleState.ACTIVE:
                raise SkillBundleError(
                    f"Skill {root.skill_id!r} is {root.lifecycle.state.value}, not ACTIVE"
                )
            roots.append(root)
        if not roots:
            raise SkillBundleError("at least one active Skill is required")
        catalog = await self._registry.all(states={SkillLifecycleState.ACTIVE})
        resolved = resolve_dependencies(roots, catalog)
        capabilities = await self._resolve_capabilities(resolved)
        try:
            prompts = {key: value for skill in resolved for key, value in skill.prompts.items()}
            bundle = SkillBundle(
                skills=resolved,
                instructions=tuple(line for skill in resolved for line in skill.instructions),
                dependency_order=tuple(skill.skill_id for skill in resolved),
                dependencies=tuple(
                    dependency for skill in resolved for dependency in skill.dependencies
                ),
                capabilities=capabilities,
                resources=tuple(resource for skill in resolved for resource in skill.resources),
                prompts=prompts,
                provenance=tuple(skill.provenance for skill in resolved),
                metadata={"root_skill_ids": ",".join(skill.skill_id for skill in roots)},
            )
            await self._emit_observability(
                "skill.bundle.built",
                root_count=len(roots),
                skill_count=len(bundle.skills),
                capability_count=len(bundle.capabilities),
            )
            return bundle
        except Exception as error:
            raise SkillBundleError(
                "could not compose resolved Skills into a SkillBundle"
            ) from error

    async def refresh(
        self,
        *,
        mode: RefreshMode = RefreshMode.FULL,
        resource_ids: Iterable[str] = (),
        trigger: TriggerSource = TriggerSource.MANUAL,
    ) -> RefreshResult | None:
        """Refresh the external engine, then ingest each healthy Skill source.

        Successful sources are committed even if another source fails. Failures are
        collected and raised after successful source data is retained.
        """
        result: RefreshResult | None = None
        if self._refresh_engine is not None:
            try:
                result = await self._refresh_engine.refresh(
                    mode=mode, resource_ids=tuple(resource_ids), trigger=trigger
                )
            except Exception as error:
                raise SkillSourceError("refresh-engine refresh failed") from error
            if result.status is RefreshStatus.FAILED:
                raise SkillSourceError("refresh-engine reported a failed Skill refresh")
        errors = await self._load_sources()
        await self._reindex_if_needed()
        self._invalidate_capabilities()
        if errors:
            raise SkillSourceError(
                "one or more Skill sources failed; healthy sources were retained: "
                + ", ".join(sorted(errors))
            )
        logger.info("skill_refresh_completed", extra={"source_count": len(self._sources)})
        await self._emit_observability(
            "skill.refresh.completed",
            source_count=len(self._sources),
            external_engine=self._refresh_engine is not None,
            source_error_count=0,
        )
        return result

    async def _emit_observability(
        self,
        name: str,
        **attributes: SkillObservabilityValue,
    ) -> None:
        try:
            await self._observability.emit(
                SkillObservabilityEvent(name=name, attributes=MappingProxyType(attributes))
            )
        except Exception as error:
            self._observability_errors.append(error)
            logger.exception("skill_observability_failed", extra={"event_name": name})

    async def schedule_refresh(self, interval: float) -> AsyncScheduler:
        """Start refresh-engine's asyncio scheduler for periodic source refresh."""
        async with self._scheduler_lock:
            if self._scheduler is not None:
                raise SkillGovernanceError("a scheduled refresh is already running")

            async def scheduled_refresh() -> None:
                await self.refresh(trigger=TriggerSource.SCHEDULED)

            self._scheduler = AsyncScheduler(scheduled_refresh, interval)
            await self._scheduler.start()
            return self._scheduler

    async def close(self) -> None:
        """Stop an owned refresh scheduler; externally injected services remain caller-owned."""
        async with self._scheduler_lock:
            if self._scheduler is not None:
                await self._scheduler.stop()
                self._scheduler = None

    async def _resolve_capabilities(
        self, skills: Sequence[Skill]
    ) -> dict[str, tuple[Capability, ...]]:
        names = sorted({capability.name for skill in skills for capability in skill.capabilities})
        if not names:
            return {}
        if self._mcp_runtime is None:
            raise CapabilityResolutionError(
                "Skills require MCP capabilities but no MCPRuntime was configured"
            )

        async def resolve(name: str) -> tuple[str, Capability]:
            lock = self._capability_locks.setdefault(name, asyncio.Lock())
            async with lock:
                while True:
                    epoch = self._capability_epoch
                    cached = self._capability_cache.get(name)
                    if cached is not None:
                        return name, cached
                    try:
                        candidates = await self._mcp_runtime.retrieve(name, limit=50)
                    except Exception as error:
                        raise CapabilityResolutionError(
                            f"MCP capability discovery failed for {name!r}"
                        ) from error
                    if epoch != self._capability_epoch:
                        continue
                    matches = [
                        item
                        for item in candidates
                        if item.name == name or item.capability_id == name
                    ]
                    if not matches:
                        raise CapabilityResolutionError(
                            f"required capability {name!r} was not found"
                        )
                    selected = min(matches, key=lambda item: item.capability_id)
                    self._capability_cache[name] = selected
                    return name, selected

        pairs = await asyncio.gather(*(resolve(name) for name in names))
        return {name: (capability,) for name, capability in pairs}

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:
                return
            await self._load_sources()
            await self._reindex_if_needed()
            self._loaded = True

    async def _load_sources(self) -> dict[str, Exception]:
        results = await asyncio.gather(*(self._load_one_source(source) for source in self._sources))
        errors = {key: error for source_errors in results for key, error in source_errors.items()}
        self._mark_index_dirty()
        return errors

    async def _load_one_source(self, source: SkillSource) -> dict[str, Exception]:
        errors: dict[str, Exception] = {}
        async with self._source_load_locks[source.source_id]:
            try:
                documents = await source.load()
            except Exception as error:
                errors[source.source_id] = error
                self._source_errors[source.source_id] = (
                    f"{type(error).__name__}: Skill source load failed"
                )
                logger.error(
                    "skill_source_load_failed",
                    extra={
                        "source_id": source.source_id,
                        "error_type": type(error).__name__,
                    },
                )
                return errors

            self._source_errors.pop(source.source_id, None)
            for old_key in tuple(self._source_errors):
                if old_key.startswith(source.source_id + ":"):
                    del self._source_errors[old_key]
            previous_documents = self._documents_by_source.get(source.source_id, {})
            current_documents: dict[str, str] = {}
            for locator, content in documents.items():
                try:
                    skill = parse_skill_yaml(content, self._validator)
                    if (
                        skill.provenance.origin is SkillOrigin.AGENT
                        and not self.config.allow_agent_skill_creation
                    ):
                        raise SkillCreationDisabledError(
                            "source cannot register an agent Skill while creation is disabled"
                        )
                    if (
                        skill.provenance.origin is SkillOrigin.AGENT
                        and self.config.require_human_approval
                        and skill.lifecycle.state is SkillLifecycleState.ACTIVE
                        and not await self._approval_is_recorded(skill)
                    ):
                        skill = skill.model_copy(
                            update={
                                "lifecycle": SkillLifecycle(
                                    state=SkillLifecycleState.PENDING_APPROVAL
                                )
                            }
                        )
                    key_lock = self._catalog_locks.setdefault(
                        (skill.metadata.name, skill.metadata.version), asyncio.Lock()
                    )
                    async with key_lock:
                        await self._registry.put(skill)
                    self._source_for_skill[skill.skill_id] = source.source_id
                    current_documents[locator] = skill.skill_id
                    logger.info(
                        "skill_loaded",
                        extra={"skill_id": skill.skill_id, "source_id": source.source_id},
                    )
                except Exception as parse_error:
                    source_key = f"{source.source_id}:{locator}"
                    self._source_errors[source_key] = (
                        f"{type(parse_error).__name__}: invalid Skill document"
                    )
                    logger.warning(
                        "invalid_skill_ignored",
                        extra={"source_id": source.source_id},
                    )
                    errors[source_key] = parse_error
                    previous_id = previous_documents.get(locator)
                    if previous_id is not None:
                        current_documents[locator] = previous_id
            for locator, previous_id in previous_documents.items():
                if locator not in current_documents:
                    try:
                        previous = await self._registry.get(previous_id)
                    except SkillNotFoundError:
                        continue
                    key_lock = self._catalog_locks.setdefault(
                        (previous.metadata.name, previous.metadata.version),
                        asyncio.Lock(),
                    )
                    async with key_lock:
                        try:
                            removed = await self._registry.remove(previous_id)
                        except SkillNotFoundError:
                            continue
                        if self._source_for_skill.get(removed.skill_id) == source.source_id:
                            self._source_for_skill.pop(removed.skill_id, None)
            self._documents_by_source[source.source_id] = current_documents
        return errors

    async def _approval_is_recorded(self, skill: Skill) -> bool:
        event_id = skill.governance.approval_event_id
        if event_id is None:
            return False
        try:
            feedback_id = UUID(event_id)
        except ValueError:
            return False
        event = await self._feedback.get(feedback_id)
        return bool(
            event is not None
            and event.target.type == "skill"
            and event.target.id == skill.skill_id
            and event.category == "approval"
            and event.status is FeedbackStatus.RESOLVED
        )

    async def _reindex_if_needed(self) -> None:
        if not self._index_dirty:
            return
        async with self._reindex_lock:
            while self._index_dirty:
                catalog_version = self._catalog_version
                skills = await self._registry.all()
                try:
                    await self._discovery.index(skills)
                except Exception as error:
                    raise SkillDiscoveryError(
                        "could not build the Skill discovery index"
                    ) from error
                if catalog_version == self._catalog_version:
                    self._index_dirty = False

    def _select_source(self, source_id: str | None) -> SkillSource | None:
        if source_id is not None:
            try:
                return self._source_by_id[source_id]
            except KeyError as error:
                raise SkillSourceError(f"unknown Skill source {source_id!r}") from error
        if not self._sources:
            return None
        return self._sources[0]

    async def _write_skill(
        self,
        skill: Skill,
        source: SkillSource | None,
        *,
        persist: bool,
    ) -> None:
        key = (skill.metadata.name, skill.metadata.version)
        key_lock = self._catalog_locks.setdefault(key, asyncio.Lock())
        if source is None:
            async with key_lock:
                await self._registry.check_put(skill)
                await self._registry.put(skill)
        else:
            async with self._source_load_locks[source.source_id]:
                async with key_lock:
                    await self._registry.check_put(skill)
                    if persist:
                        try:
                            await source.save(skill)
                        except Exception as error:
                            raise SkillSourceError(
                                f"cannot persist Skill {skill.skill_id!r} "
                                f"to source {source.source_id!r}"
                            ) from error
                    await self._registry.put(skill)
                    self._source_for_skill[skill.skill_id] = source.source_id
        self._mark_index_dirty()

    async def _replace_lifecycle(
        self,
        skill: Skill,
        *,
        expected: SkillLifecycleState,
        source: SkillSource | None,
    ) -> None:
        key = (skill.metadata.name, skill.metadata.version)
        key_lock = self._catalog_locks.setdefault(key, asyncio.Lock())
        source_lock = self._source_load_locks[source.source_id] if source is not None else None
        if source_lock is not None:
            await source_lock.acquire()
        try:
            async with key_lock:
                current = await self._registry.get(skill.skill_id)
                if current.lifecycle.state is not expected:
                    raise SkillLifecycleError(
                        f"Skill {skill.skill_id!r} changed during a lifecycle transition"
                    )
                if source is not None:
                    await source.save(skill)
                await self._registry.replace_lifecycle(skill)
        finally:
            if source_lock is not None:
                source_lock.release()
        self._mark_index_dirty()

    def _mark_index_dirty(self) -> None:
        self._catalog_version += 1
        self._index_dirty = True

    def _invalidate_capabilities(self) -> None:
        self._capability_epoch += 1
        self._capability_cache.clear()

    def _require_agent_creation(self) -> None:
        if not self.config.allow_agent_skill_creation:
            raise SkillCreationDisabledError("agent-generated Skill creation is disabled")


def make_skill_revision(
    parent: Skill,
    *,
    instructions: Sequence[str],
    dependencies: Sequence[SkillDependency] = (),
) -> Skill:
    """Create a new agent revision linked to its rejected parent."""
    return Skill(
        metadata=parent.metadata,
        instructions=tuple(instructions),
        dependencies=tuple(dependencies),
        capabilities=parent.capabilities,
        resources=parent.resources,
        prompts=parent.prompts,
        revision=parent.revision + 1,
        provenance=SkillProvenance(
            origin=SkillOrigin.AGENT,
            source="revision",
            parent_skill_ids=(parent.skill_id,),
        ),
        lifecycle=SkillLifecycle(state=SkillLifecycleState.ACTIVE),
    )
