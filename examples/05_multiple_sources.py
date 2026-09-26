import asyncio
import sqlite3
from collections.abc import Mapping
from pathlib import Path

import yaml
from _common import make_skill

from skill_manager import FilesystemSkillSource, Skill, SkillManager, SkillSource


class SQLiteSkillSource(SkillSource):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS skills (skill_id TEXT PRIMARY KEY, yaml TEXT NOT NULL)"
            )

    @property
    def source_id(self) -> str:
        return "sqlite"

    async def load(self) -> Mapping[str, str]:
        def read() -> dict[str, str]:
            with sqlite3.connect(self.path) as connection:
                rows = connection.execute("SELECT skill_id, yaml FROM skills").fetchall()
            return {str(skill_id): str(document) for skill_id, document in rows}

        return await asyncio.to_thread(read)

    async def save(self, skill: Skill) -> None:
        document = yaml.safe_dump(skill.model_dump(mode="json"), sort_keys=True)

        def write() -> None:
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    "INSERT INTO skills(skill_id, yaml) VALUES (?, ?) "
                    "ON CONFLICT(skill_id) DO UPDATE SET yaml=excluded.yaml",
                    (skill.skill_id, document),
                )

        await asyncio.to_thread(write)

    async def delete(self, skill_id: str) -> None:
        def remove() -> None:
            with sqlite3.connect(self.path) as connection:
                connection.execute("DELETE FROM skills WHERE skill_id = ?", (skill_id,))

        await asyncio.to_thread(remove)


async def main() -> None:
    filesystem = FilesystemSkillSource(Path("skills/filesystem"), source_id="filesystem")
    database = SQLiteSkillSource(Path("skills/catalog.sqlite3"))
    first = make_skill(
        "filesystem-skill",
        "Stored as a YAML source document",
        skill_id="sk_00000000000000000000000002",
    )
    second = make_skill(
        "database-skill",
        "Stored in an application-owned SQLite table",
        skill_id="sk_00000000000000000000000003",
    )
    await filesystem.save(first)
    await database.save(second)
    manager = SkillManager(sources=[filesystem, database])
    print((await manager.load(first.skill_id)).metadata.name)
    print((await manager.load(second.skill_id)).metadata.name)


if __name__ == "__main__":
    asyncio.run(main())
