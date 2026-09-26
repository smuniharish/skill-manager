"""Composable retrieval and reranking for bounded Skill discovery."""

from __future__ import annotations

import asyncio
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.embeddings import Embeddings

from skill_manager.errors import SkillDiscoveryError
from skill_manager.models import Skill, SkillLifecycleState

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.]*", re.I)


@dataclass(frozen=True, slots=True)
class RetrievedSkill:
    """A retrieved Skill candidate and its backend-specific relevance score."""

    skill: Skill
    score: float


class SkillRetriever(ABC):
    """Public extension point for indexing and retrieving Skill candidates."""

    @abstractmethod
    async def index(self, skills: Sequence[Skill]) -> None:
        """Replace the retriever's catalog snapshot."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedSkill]:
        """Return at most ``limit`` active, filtered candidates."""


class SkillReranker(ABC):
    """Public extension point for final candidate ordering."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedSkill],
        *,
        top_k: int,
    ) -> list[Skill]:
        """Return at most ``top_k`` candidates in final relevance order."""


class DiscoveryProvider(ABC):
    """Public extension point for indexed, bounded Skill discovery."""

    @abstractmethod
    async def index(self, skills: Sequence[Skill]) -> None:
        """Replace the discoverable catalog snapshot."""

    @abstractmethod
    async def discover(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Skill]:
        """Return at most ``top_k`` active candidates."""


def _matches(skill: Skill, filters: Mapping[str, Any] | None) -> bool:
    if skill.lifecycle.state is not SkillLifecycleState.ACTIVE:
        return False
    if not filters:
        return True
    for key, expected in filters.items():
        if key == "name" and skill.metadata.name != expected:
            return False
        if key == "version" and skill.metadata.version != expected:
            return False
        if key == "tag" and expected not in skill.metadata.tags:
            return False
        if key == "capability" and expected not in {
            capability.name for capability in skill.capabilities
        }:
            return False
        if key not in {"name", "version", "tag", "capability"}:
            raise SkillDiscoveryError(f"unsupported Skill discovery filter: {key!r}")
    return True


def _document(skill: Skill) -> str:
    return "\n".join(
        (
            skill.metadata.name,
            skill.metadata.description,
            " ".join(skill.metadata.tags),
            "\n".join(skill.instructions),
            " ".join(capability.name for capability in skill.capabilities),
        )
    )


class LexicalSkillRetriever(SkillRetriever):
    """Deterministic inverted-index retrieval over Skill domain text."""

    def __init__(self) -> None:
        self._skills: tuple[Skill, ...] = ()
        self._postings: dict[str, frozenset[str]] = {}
        self._by_id: dict[str, Skill] = {}

    async def index(self, skills: Sequence[Skill]) -> None:
        by_id = {
            skill.skill_id: skill
            for skill in skills
            if skill.lifecycle.state is SkillLifecycleState.ACTIVE
        }
        postings: dict[str, set[str]] = {}
        for skill in by_id.values():
            for token in set(_TOKEN_PATTERN.findall(_document(skill).lower())):
                postings.setdefault(token, set()).add(skill.skill_id)
        self._skills = tuple(by_id.values())
        self._by_id = by_id
        self._postings = {token: frozenset(ids) for token, ids in postings.items()}

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedSkill]:
        if limit < 1:
            raise SkillDiscoveryError("retrieval limit must be at least 1")
        terms = tuple(dict.fromkeys(_TOKEN_PATTERN.findall(query.lower())))
        if not terms:
            candidates = self._skills
        else:
            candidate_ids = set().union(*(self._postings.get(term, frozenset()) for term in terms))
            candidates = tuple(self._by_id[item] for item in candidate_ids)
        retrieved = [
            RetrievedSkill(
                skill=skill,
                score=float(sum(term in _document(skill).lower() for term in terms)),
            )
            for skill in candidates
            if _matches(skill, filters)
        ]
        retrieved.sort(key=lambda item: (-item.score, item.skill.skill_id))
        return retrieved[:limit]


class SemanticSkillRetriever(SkillRetriever):
    """Dense retrieval backed by an injected LangChain Embeddings object."""

    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings
        self._skills: tuple[Skill, ...] = ()
        self._vectors: tuple[list[float], ...] = ()
        self._index_lock = asyncio.Lock()

    async def index(self, skills: Sequence[Skill]) -> None:
        active = tuple(
            skill for skill in skills if skill.lifecycle.state is SkillLifecycleState.ACTIVE
        )
        try:
            vectors = tuple(
                await self._embeddings.aembed_documents([_document(skill) for skill in active])
            )
        except Exception as error:
            raise SkillDiscoveryError("semantic Skill index embedding failed") from error
        async with self._index_lock:
            self._skills = active
            self._vectors = vectors

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedSkill]:
        if limit < 1:
            raise SkillDiscoveryError("retrieval limit must be at least 1")
        async with self._index_lock:
            skills, vectors = self._skills, self._vectors
        try:
            query_vector = await self._embeddings.aembed_query(query)
        except Exception as error:
            raise SkillDiscoveryError("semantic Skill query embedding failed") from error
        retrieved: list[RetrievedSkill] = []
        for skill, vector in zip(skills, vectors, strict=True):
            if not _matches(skill, filters):
                continue
            dot = sum(left * right for left, right in zip(query_vector, vector, strict=True))
            norm = math.sqrt(sum(value * value for value in query_vector)) * math.sqrt(
                sum(value * value for value in vector)
            )
            retrieved.append(RetrievedSkill(skill=skill, score=dot / norm if norm else 0.0))
        retrieved.sort(key=lambda item: (-item.score, item.skill.skill_id))
        return retrieved[:limit]


class ScoreSkillReranker(SkillReranker):
    """Default deterministic reranker using retrieval score and Skill ID."""

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedSkill],
        *,
        top_k: int,
    ) -> list[Skill]:
        del query
        ranked = sorted(candidates, key=lambda item: (-item.score, item.skill.skill_id))
        return [item.skill for item in ranked[:top_k]]


class PipelineDiscoveryProvider(DiscoveryProvider):
    """Compose an injected retriever and reranker into bounded discovery."""

    def __init__(
        self,
        retriever: SkillRetriever,
        *,
        reranker: SkillReranker | None = None,
        candidate_pool_size: int = 50,
    ) -> None:
        if candidate_pool_size < 1:
            raise ValueError("candidate_pool_size must be at least 1")
        self._retriever = retriever
        self._reranker = reranker or ScoreSkillReranker()
        self._candidate_pool_size = candidate_pool_size

    async def index(self, skills: Sequence[Skill]) -> None:
        await self._retriever.index(skills)

    async def discover(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Skill]:
        if top_k < 1:
            raise SkillDiscoveryError("top_k must be at least 1")
        retrieval_limit = max(top_k, self._candidate_pool_size)
        candidates = await self._retriever.retrieve(
            query,
            limit=retrieval_limit,
            filters=filters,
        )
        if len(candidates) > retrieval_limit:
            raise SkillDiscoveryError("Skill retriever returned more than its candidate limit")
        safe_candidates = tuple(
            candidate for candidate in candidates if _matches(candidate.skill, filters)
        )
        ranked = await self._reranker.rerank(query, safe_candidates, top_k=top_k)
        if len(ranked) > top_k:
            raise SkillDiscoveryError("Skill reranker returned more than top_k candidates")
        candidate_by_id = {
            candidate.skill.skill_id: candidate.skill for candidate in safe_candidates
        }
        seen: set[str] = set()
        for skill in ranked:
            if (
                candidate_by_id.get(skill.skill_id) != skill
                or skill.skill_id in seen
                or not _matches(skill, filters)
            ):
                raise SkillDiscoveryError("Skill reranker returned an invalid candidate set")
            seen.add(skill.skill_id)
        return ranked


class ExactDiscoveryProvider(PipelineDiscoveryProvider):
    """Default lexical retrieval and score-based reranking pipeline."""

    def __init__(
        self,
        *,
        retriever: SkillRetriever | None = None,
        reranker: SkillReranker | None = None,
        candidate_pool_size: int = 50,
    ) -> None:
        super().__init__(
            retriever or LexicalSkillRetriever(),
            reranker=reranker,
            candidate_pool_size=candidate_pool_size,
        )


class SemanticDiscoveryProvider(PipelineDiscoveryProvider):
    """Semantic retrieval with an optional custom reranker."""

    def __init__(
        self,
        embeddings: Embeddings,
        *,
        reranker: SkillReranker | None = None,
        candidate_pool_size: int = 50,
    ) -> None:
        super().__init__(
            SemanticSkillRetriever(embeddings),
            reranker=reranker,
            candidate_pool_size=candidate_pool_size,
        )
