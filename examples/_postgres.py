"""Reusable PostgreSQL Skill source and registry example implementations."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import asyncpg
import yaml
from _common import make_skill
from asyncpg import Connection, Pool
from packaging.version import InvalidVersion, Version

from skill_manager import (
    Skill,
    SkillConflictError,
    SkillLifecycleState,
    SkillManager,
    SkillNotFoundError,
    SkillRegistry,
    SkillSource,
)


class PostgresService:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Pool | None = None

    async def open(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def require_pool(self) -> Pool:
        if self._pool is None:
            raise RuntimeError("open() must be called before database use")
        return self._pool


class PostgresSkillSource(PostgresService, SkillSource):
    def __init__(self, dsn: str) -> None:
        super().__init__(dsn)

    @property
    def source_id(self) -> str:
        return "postgres"

    async def open(self) -> None:
        await super().open()
        pool = self.require_pool()
        try:
            await pool.execute("""
                CREATE TABLE IF NOT EXISTS skill_documents (
                    skill_id TEXT PRIMARY KEY,
                    yaml TEXT NOT NULL
                )
                """)
        except Exception:
            await self.close()
            raise

    async def load(self) -> Mapping[str, str]:
        rows = await self.require_pool().fetch(
            "SELECT skill_id, yaml FROM skill_documents ORDER BY skill_id"
        )
        return {str(row["skill_id"]): str(row["yaml"]) for row in rows}

    async def save(self, skill: Skill) -> None:
        document = yaml.safe_dump(skill.model_dump(mode="json"), allow_unicode=True, sort_keys=True)
        await self.require_pool().execute(
            """
            INSERT INTO skill_documents (skill_id, yaml)
            VALUES ($1, $2)
            ON CONFLICT (skill_id) DO UPDATE SET yaml = EXCLUDED.yaml
            """,
            skill.skill_id,
            document,
        )

    async def delete(self, skill_id: str) -> None:
        await self.require_pool().execute(
            "DELETE FROM skill_documents WHERE skill_id = $1", skill_id
        )


class PostgresSkillRegistry(PostgresService, SkillRegistry):
    async def open(self) -> None:
        await super().open()
        pool = self.require_pool()
        try:
            await pool.execute("""
                CREATE TABLE IF NOT EXISTS skill_registry (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    document JSONB NOT NULL
                )
                """)
            await pool.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_active_skill_name_version
                ON skill_registry (name, version)
                WHERE lifecycle_state = 'ACTIVE'
                """)
        except Exception:
            await self.close()
            raise

    @staticmethod
    def _decode(document: Any) -> Skill:
        if isinstance(document, str):
            return Skill.model_validate_json(document)
        return Skill.model_validate(document)

    @staticmethod
    async def _lock_catalog_key(connection: Connection, skill: Skill) -> None:
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
            json.dumps([skill.metadata.name, skill.metadata.version]),
        )

    async def _check_put(self, connection: Connection, skill: Skill) -> None:
        await self._lock_catalog_key(connection, skill)
        existing_row = await connection.fetchrow(
            "SELECT document FROM skill_registry WHERE skill_id = $1 FOR UPDATE",
            skill.skill_id,
        )
        if existing_row is not None:
            existing = self._decode(existing_row["document"])
            if existing.revision > skill.revision:
                raise SkillConflictError(f"stale update for Skill {skill.skill_id!r}")
            if existing.revision == skill.revision and existing.model_dump(
                mode="json"
            ) != skill.model_dump(mode="json"):
                raise SkillConflictError(
                    f"immutable Skill revision {skill.skill_id!r} cannot be overwritten"
                )
        if skill.lifecycle.state is SkillLifecycleState.ACTIVE:
            conflicting_id = await connection.fetchval(
                """
                SELECT skill_id
                FROM skill_registry
                WHERE name = $1
                  AND version = $2
                  AND lifecycle_state = 'ACTIVE'
                  AND skill_id <> $3
                LIMIT 1
                """,
                skill.metadata.name,
                skill.metadata.version,
                skill.skill_id,
            )
            if conflicting_id is not None:
                raise SkillConflictError(
                    f"multiple active revisions for Skill {skill.metadata.name!r} "
                    f"version {skill.metadata.version!r}"
                )

    async def put(self, skill: Skill) -> None:
        document = json.dumps(skill.model_dump(mode="json"))
        async with self.require_pool().acquire() as connection:
            async with connection.transaction():
                await self._check_put(connection, skill)
                try:
                    await connection.execute(
                        """
                        INSERT INTO skill_registry (
                            skill_id, name, version, lifecycle_state, revision, document
                        )
                        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                        ON CONFLICT (skill_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            version = EXCLUDED.version,
                            lifecycle_state = EXCLUDED.lifecycle_state,
                            revision = EXCLUDED.revision,
                            document = EXCLUDED.document
                        """,
                        skill.skill_id,
                        skill.metadata.name,
                        skill.metadata.version,
                        skill.lifecycle.state.value,
                        skill.revision,
                        document,
                    )
                except asyncpg.UniqueViolationError as error:
                    raise SkillConflictError(
                        f"multiple active revisions for Skill {skill.metadata.name!r} "
                        f"version {skill.metadata.version!r}"
                    ) from error

    async def check_put(self, skill: Skill) -> None:
        async with self.require_pool().acquire() as connection:
            async with connection.transaction():
                await self._check_put(connection, skill)

    async def get(self, skill_id: str) -> Skill:
        row = await self.require_pool().fetchrow(
            "SELECT document FROM skill_registry WHERE skill_id = $1", skill_id
        )
        if row is None:
            raise SkillNotFoundError(f"Skill {skill_id!r} was not found")
        return self._decode(row["document"])

    async def by_name(self, name: str, version: str | None = None) -> Skill:
        if version is None:
            rows = await self.require_pool().fetch(
                """
                SELECT document
                FROM skill_registry
                WHERE name = $1 AND lifecycle_state = 'ACTIVE'
                """,
                name,
            )
        else:
            rows = await self.require_pool().fetch(
                """
                SELECT document
                FROM skill_registry
                WHERE name = $1
                  AND version = $2
                  AND lifecycle_state = 'ACTIVE'
                """,
                name,
                version,
            )
        matches = tuple(self._decode(row["document"]) for row in rows)
        if not matches:
            raise SkillNotFoundError(f"Skill {name!r} version {version!r} was not found")
        if version is not None:
            return matches[0]
        try:
            return max(
                matches,
                key=lambda item: (Version(item.metadata.version), item.skill_id),
            )
        except InvalidVersion as error:
            raise SkillConflictError(f"invalid catalog version for Skill {name!r}") from error

    async def all(self, *, states: set[SkillLifecycleState] | None = None) -> tuple[Skill, ...]:
        if states is None:
            rows = await self.require_pool().fetch(
                "SELECT document FROM skill_registry ORDER BY skill_id"
            )
        else:
            rows = await self.require_pool().fetch(
                """
                SELECT document
                FROM skill_registry
                WHERE lifecycle_state = ANY($1::text[])
                ORDER BY skill_id
                """,
                [state.value for state in states],
            )
        return tuple(self._decode(row["document"]) for row in rows)

    async def remove(self, skill_id: str) -> Skill:
        row = await self.require_pool().fetchrow(
            """
            DELETE FROM skill_registry
            WHERE skill_id = $1
            RETURNING document
            """,
            skill_id,
        )
        if row is None:
            raise SkillNotFoundError(f"Skill {skill_id!r} was not found")
        return self._decode(row["document"])

    async def replace_lifecycle(self, skill: Skill) -> None:
        document = json.dumps(skill.model_dump(mode="json"))
        async with self.require_pool().acquire() as connection:
            async with connection.transaction():
                await self._lock_catalog_key(connection, skill)
                exists = await connection.fetchval(
                    "SELECT 1 FROM skill_registry WHERE skill_id = $1 FOR UPDATE",
                    skill.skill_id,
                )
                if exists is None:
                    raise SkillNotFoundError(f"Skill {skill.skill_id!r} was not found")
                if skill.lifecycle.state is SkillLifecycleState.ACTIVE:
                    conflicting_id = await connection.fetchval(
                        """
                        SELECT skill_id
                        FROM skill_registry
                        WHERE name = $1
                          AND version = $2
                          AND lifecycle_state = 'ACTIVE'
                          AND skill_id <> $3
                        LIMIT 1
                        """,
                        skill.metadata.name,
                        skill.metadata.version,
                        skill.skill_id,
                    )
                    if conflicting_id is not None:
                        raise SkillConflictError(
                            f"another active revision already exists for "
                            f"{skill.metadata.name!r}"
                        )
                try:
                    await connection.execute(
                        """
                        UPDATE skill_registry
                        SET name = $2,
                            version = $3,
                            lifecycle_state = $4,
                            revision = $5,
                            document = $6::jsonb
                        WHERE skill_id = $1
                        """,
                        skill.skill_id,
                        skill.metadata.name,
                        skill.metadata.version,
                        skill.lifecycle.state.value,
                        skill.revision,
                        document,
                    )
                except asyncpg.UniqueViolationError as error:
                    raise SkillConflictError(
                        f"another active revision already exists for " f"{skill.metadata.name!r}"
                    ) from error


async def main() -> None:
    dsn = os.environ["SKILL_MANAGER_POSTGRES_DSN"]
    source = PostgresSkillSource(dsn)
    writer_registry = PostgresSkillRegistry(dsn)
    await source.open()
    await writer_registry.open()
    try:
        skill = make_skill(
            f"postgres-storage-{uuid4().hex[:8]}",
            "Demonstrate PostgreSQL-backed source and registry persistence",
        )
        writer = SkillManager(sources=[source], registry=writer_registry)
        await writer.register_skill(skill, source_id=source.source_id)

        source_reader = SkillManager(sources=[source])
        source_loaded = await source_reader.load(skill.skill_id)

        reader_registry = PostgresSkillRegistry(dsn)
        await reader_registry.open()
        try:
            registry_reader = SkillManager(registry=reader_registry)
            registry_loaded = await registry_reader.load(skill.skill_id)
            assert await reader_registry.by_name(skill.metadata.name) == skill

            rejected = skill.model_copy(
                update={
                    "lifecycle": skill.lifecycle.model_copy(
                        update={"state": SkillLifecycleState.REJECTED}
                    )
                }
            )
            await reader_registry.replace_lifecycle(rejected)
            assert await reader_registry.all(states={SkillLifecycleState.REJECTED}) == (rejected,)
            await reader_registry.replace_lifecycle(skill)

            conflicting = make_skill(
                skill.metadata.name,
                "Conflict used to verify registry uniqueness",
            )
            try:
                await reader_registry.check_put(conflicting)
            except SkillConflictError:
                pass
            else:
                raise AssertionError("registry accepted two active Skills with one name/version")

            removable = make_skill(
                f"postgres-removal-{uuid4().hex[:8]}",
                "Verify registry removal",
            )
            await reader_registry.put(removable)
            assert await reader_registry.remove(removable.skill_id) == removable
        finally:
            await reader_registry.close()

        print(f"source loaded {source_loaded.metadata.name}")
        print(f"registry loaded {registry_loaded.metadata.name}")
        print("registry lifecycle, conflict, and removal checks passed")
    finally:
        await writer_registry.close()
        await source.close()


if __name__ == "__main__":
    asyncio.run(main())
