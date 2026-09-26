"""Compose application-specific Skill retrieval and reranking."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

from _common import make_skill

from skill_manager import (
    RetrievedSkill,
    Skill,
    SkillManager,
    SkillReranker,
    SkillRetriever,
)


class AliasRetriever(SkillRetriever):
    def __init__(self) -> None:
        self._skills: tuple[Skill, ...] = ()

    async def index(self, skills: Sequence[Skill]) -> None:
        self._skills = tuple(skills)

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedSkill]:
        terms = set(query.lower().split())
        if "database" in terms:
            terms.update({"postgres", "sql"})
        candidates: list[RetrievedSkill] = []
        for skill in self._skills:
            if filters and filters.get("tag") not in skill.metadata.tags:
                continue
            text = (
                f"{skill.metadata.name} {skill.metadata.description} "
                f"{' '.join(skill.metadata.tags)}"
            ).lower()
            score = float(sum(term in text for term in terms))
            if score:
                candidates.append(RetrievedSkill(skill=skill, score=score))
        candidates.sort(key=lambda item: (-item.score, item.skill.skill_id))
        return candidates[:limit]


class ProductionTagReranker(SkillReranker):
    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedSkill],
        *,
        top_k: int,
    ) -> list[Skill]:
        del query
        ranked = sorted(
            candidates,
            key=lambda item: (
                "production" not in item.skill.metadata.tags,
                -item.score,
                item.skill.skill_id,
            ),
        )
        return [item.skill for item in ranked[:top_k]]


async def main() -> None:
    manager = SkillManager(
        retriever=AliasRetriever(),
        reranker=ProductionTagReranker(),
        discovery_candidate_pool_size=10,
    )
    general = make_skill("sql-review", "Review SQL statements")
    production = make_skill("postgres-operations", "Operate PostgreSQL safely")
    production = production.model_copy(
        update={
            "metadata": production.metadata.model_copy(update={"tags": ("postgres", "production")})
        }
    )
    await manager.register_skill(general)
    await manager.register_skill(production)

    matches = await manager.discover("database review", top_k=2)
    print([skill.metadata.name for skill in matches])


if __name__ == "__main__":
    asyncio.run(main())
