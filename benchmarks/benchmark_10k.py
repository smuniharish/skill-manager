"""Reproducible local measurements; synthetic embeddings measure plumbing only."""

from __future__ import annotations

import asyncio
import time
import tracemalloc
from collections.abc import Mapping

import yaml
from langchain_core.embeddings import DeterministicFakeEmbedding
from mcp_capability_router import MCPRuntime, Tool

from examples._common import make_skill
from skill_manager import (
    SemanticDiscoveryProvider,
    Skill,
    SkillCapability,
    SkillDependency,
    SkillManager,
    SkillSource,
)
from skill_manager.discovery import ExactDiscoveryProvider
from skill_manager.resolution import resolve_dependencies


class CatalogSource(SkillSource):
    def __init__(self, documents: Mapping[str, str]) -> None:
        self.documents = documents

    @property
    def source_id(self) -> str:
        return "benchmark-catalog"

    async def load(self) -> Mapping[str, str]:
        return self.documents

    async def save(self, skill: Skill) -> None:
        raise RuntimeError("benchmark source is read-only")

    async def delete(self, skill_id: str) -> None:
        raise RuntimeError("benchmark source is read-only")


def elapsed(start: float) -> float:
    return time.perf_counter() - start


async def main() -> None:
    tracemalloc.start()
    start = time.perf_counter()
    skills = [
        make_skill(
            f"catalog-skill-{index:05}",
            f"Catalog entry {index} for application domain search",
        )
        for index in range(10_000)
    ]
    construction_seconds = elapsed(start)
    documents = {
        skill.skill_id: yaml.safe_dump(skill.model_dump(mode="json"), sort_keys=True)
        for skill in skills
    }
    manager_load = SkillManager(sources=[CatalogSource(documents)])
    start = time.perf_counter()
    await manager_load.load(skills[0].skill_id)
    source_load_seconds = elapsed(start)

    exact = ExactDiscoveryProvider()
    start = time.perf_counter()
    await exact.index(skills)
    exact_index_seconds = elapsed(start)
    start = time.perf_counter()
    exact_matches = await exact.discover("domain search", top_k=10)
    exact_discovery_seconds = elapsed(start)

    semantic = SemanticDiscoveryProvider(DeterministicFakeEmbedding(size=32))
    start = time.perf_counter()
    await semantic.index(skills)
    semantic_index_seconds = elapsed(start)
    start = time.perf_counter()
    await semantic.discover("domain search", top_k=10)
    semantic_discovery_seconds = elapsed(start)

    chain = [make_skill("f", "Dependency f")]
    for child, parent in zip("edcba", "fedcb", strict=True):
        chain.append(make_skill(child, f"Dependency {child}", SkillDependency(name=parent)))
    start = time.perf_counter()
    resolve_dependencies((chain[-1],), chain)
    dependency_seconds = elapsed(start)

    runtime = MCPRuntime()
    capability = Tool(
        capability_id="benchmark:tool:catalog.read",
        server_id="benchmark",
        name="catalog.read",
        description="Read indexed catalog records",
    )
    await runtime.registry.upsert_many([capability])
    manager = SkillManager(mcp_runtime=runtime)
    target = make_skill(
        "bundle-target",
        "Read catalog records",
    ).model_copy(update={"capabilities": (SkillCapability(name="catalog.read"),)})
    await manager.register_skill(target)
    start = time.perf_counter()
    bundle = await manager.build_bundle((target,))
    bundle_seconds = elapsed(start)

    start = time.perf_counter()
    await asyncio.gather(*(exact.discover("domain search", top_k=5) for _ in range(100)))
    concurrent_seconds = elapsed(start)
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    await runtime.close()

    print(
        {
            "catalog_size": len(skills),
            "skill_model_construction_seconds": construction_seconds,
            "yaml_source_load_validate_index_seconds": source_load_seconds,
            "exact_index_seconds": exact_index_seconds,
            "exact_top10_seconds": exact_discovery_seconds,
            "semantic_fake_embedding_index_seconds": semantic_index_seconds,
            "semantic_fake_embedding_query_seconds": semantic_discovery_seconds,
            "six_skill_dependency_resolution_seconds": dependency_seconds,
            "one_skill_capability_bundle_seconds": bundle_seconds,
            "100_concurrent_queries_seconds": concurrent_seconds,
            "bounded_exact_result_count": len(exact_matches),
            "bundle_skill_count": len(bundle.skills),
            "current_traced_bytes": current_bytes,
            "peak_traced_bytes": peak_bytes,
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
