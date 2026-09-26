"""Example app: semantic Skill discovery using local Ollama embeddings."""

from __future__ import annotations

import asyncio
import os

from _common import make_skill
from langchain_ollama import OllamaEmbeddings

from skill_manager import SemanticDiscoveryProvider, SkillManager


async def main() -> None:
    embeddings = OllamaEmbeddings(
        model=os.getenv("SKILL_MANAGER_EMBEDDING_MODEL", "nomic-embed-text"),
        base_url=os.getenv("SKILL_MANAGER_OLLAMA_URL", "http://127.0.0.1:11434"),
    )
    manager = SkillManager(discovery_provider=SemanticDiscoveryProvider(embeddings))
    for skill in (
        make_skill(
            "postgres-deadlock-analysis",
            "Diagnose PostgreSQL deadlocks, lock waits, and transaction contention.",
        ),
        make_skill(
            "python-style-review",
            "Review Python formatting, lint findings, and naming conventions.",
        ),
        make_skill(
            "incident-summary",
            "Summarize operational incidents and customer impact.",
        ),
    ):
        await manager.register_skill(skill)

    matches = await manager.discover(
        "Why does one database transaction block another?",
        top_k=1,
    )
    print([skill.metadata.name for skill in matches])


if __name__ == "__main__":
    asyncio.run(main())
