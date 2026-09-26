import asyncio

from _common import make_skill
from langchain_core.embeddings import DeterministicFakeEmbedding

from skill_manager import SemanticDiscoveryProvider, SkillManager


async def main() -> None:
    provider = SemanticDiscoveryProvider(DeterministicFakeEmbedding(size=64))
    manager = SkillManager(discovery_provider=provider)
    await manager.register_skill(
        make_skill("database-lock-analysis", "Investigate database concurrency stalls")
    )
    await manager.register_skill(make_skill("python-formatting", "Apply consistent Python style"))
    matches = await manager.discover("diagnose a transaction blocking another", top_k=2)
    print([skill.metadata.name for skill in matches])


if __name__ == "__main__":
    asyncio.run(main())
