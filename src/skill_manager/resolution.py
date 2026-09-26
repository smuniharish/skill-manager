"""Deterministic dependency resolution and SkillBundle composition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from skill_manager.errors import (
    SkillConflictError,
    SkillDependencyCycleError,
    SkillDependencyError,
)
from skill_manager.models import Skill, SkillDependency, SkillLifecycleState


@dataclass(frozen=True)
class _Requirement:
    parent: Skill
    dependency: SkillDependency
    path: tuple[str, ...]


def resolve_dependencies(roots: Iterable[Skill], catalog: Iterable[Skill]) -> tuple[Skill, ...]:
    """Return a deterministic dependency-first resolution satisfying shared constraints."""
    available = tuple(
        skill for skill in catalog if skill.lifecycle.state is SkillLifecycleState.ACTIVE
    )
    sorted_roots = tuple(
        sorted(
            roots,
            key=lambda item: (item.metadata.name, Version(item.metadata.version), item.skill_id),
        )
    )
    assignments: dict[str, Skill] = {}
    for root in sorted_roots:
        existing = assignments.get(root.metadata.name)
        if existing is not None and existing.skill_id != root.skill_id:
            raise SkillConflictError(
                f"multiple root revisions selected for Skill {root.metadata.name!r}"
            )
        assignments[root.metadata.name] = root

    def matching(dependency: SkillDependency) -> list[Skill]:
        spec = SpecifierSet("" if dependency.version == "*" else dependency.version)
        try:
            matches = [
                skill
                for skill in available
                if skill.metadata.name == dependency.name
                and Version(skill.metadata.version) in spec
            ]
            return sorted(
                matches,
                key=lambda item: (Version(item.metadata.version), item.skill_id),
                reverse=True,
            )
        except InvalidVersion as error:
            raise SkillDependencyError(
                f"invalid semantic version while resolving {dependency.name!r}"
            ) from error

    def enqueue_children(
        skill: Skill,
        path: tuple[str, ...],
    ) -> tuple[_Requirement, ...]:
        return tuple(
            _Requirement(skill, dependency, path)
            for dependency in sorted(skill.dependencies, key=lambda item: item.name)
        )

    def topological_order(
        chosen: dict[str, Skill],
        edges: dict[str, set[str]],
    ) -> tuple[Skill, ...]:
        by_id = {skill.skill_id: skill for skill in chosen.values()}
        visiting: list[str] = []
        visited: set[str] = set()
        result: list[Skill] = []

        def visit(skill_id: str) -> None:
            if skill_id in visiting:
                start = visiting.index(skill_id)
                cycle_ids = (*visiting[start:], skill_id)
                raise SkillDependencyCycleError(
                    tuple(by_id[item].metadata.name for item in cycle_ids)
                )
            if skill_id in visited:
                return
            visiting.append(skill_id)
            skill = by_id[skill_id]
            children = sorted(
                edges.get(skill_id, set()),
                key=lambda item: (
                    by_id[item].metadata.name,
                    Version(by_id[item].metadata.version),
                    item,
                ),
            )
            for child_id in children:
                visit(child_id)
            visiting.pop()
            visited.add(skill_id)
            result.append(skill)

        for skill in sorted(
            by_id.values(),
            key=lambda item: (
                item.metadata.name,
                Version(item.metadata.version),
                item.skill_id,
            ),
        ):
            visit(skill.skill_id)
        return tuple(result)

    def search(
        pending: tuple[_Requirement, ...],
        chosen: dict[str, Skill],
        edges: dict[str, set[str]],
        expanded: frozenset[str],
    ) -> tuple[Skill, ...]:
        if not pending:
            return topological_order(chosen, edges)

        requirement, remaining = pending[0], pending[1:]
        dependency = requirement.dependency
        path = (*requirement.path, requirement.parent.metadata.name, dependency.name)
        options = matching(dependency)
        if not options:
            raise SkillDependencyError(
                "missing dependency along path "
                + " -> ".join(path)
                + f" (requires {dependency.version})"
            )

        selected = chosen.get(dependency.name)
        if selected is not None:
            spec = SpecifierSet("" if dependency.version == "*" else dependency.version)
            if Version(selected.metadata.version) not in spec:
                raise SkillConflictError(
                    "conflicting dependency constraints along path " + " -> ".join(path)
                )
            next_edges = {key: set(value) for key, value in edges.items()}
            next_edges.setdefault(requirement.parent.skill_id, set()).add(selected.skill_id)
            next_pending = remaining
            next_expanded = expanded
            if selected.skill_id not in expanded:
                next_pending = (
                    *enqueue_children(
                        selected, (*requirement.path, requirement.parent.metadata.name)
                    ),
                    *remaining,
                )
                next_expanded = expanded | {selected.skill_id}
            return search(next_pending, chosen, next_edges, next_expanded)

        failures: list[SkillDependencyError | SkillConflictError] = []
        for candidate in options:
            next_chosen = dict(chosen)
            next_chosen[dependency.name] = candidate
            next_edges = {key: set(value) for key, value in edges.items()}
            next_edges.setdefault(requirement.parent.skill_id, set()).add(candidate.skill_id)
            next_pending = remaining
            next_expanded = expanded
            if candidate.skill_id not in expanded:
                next_pending = (
                    *enqueue_children(
                        candidate,
                        (*requirement.path, requirement.parent.metadata.name),
                    ),
                    *remaining,
                )
                next_expanded = expanded | {candidate.skill_id}
            try:
                return search(next_pending, next_chosen, next_edges, next_expanded)
            except (SkillDependencyError, SkillConflictError) as error:
                failures.append(error)
        raise failures[0]

    pending = tuple(
        requirement for root in sorted_roots for requirement in enqueue_children(root, ())
    )
    initial_edges = {root.skill_id: set() for root in sorted_roots}
    try:
        return search(
            pending,
            assignments,
            initial_edges,
            frozenset(root.skill_id for root in sorted_roots),
        )
    except (SkillDependencyError, SkillConflictError):
        raise
