"""Safe YAML parsing and Skill domain validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import yaml
from pydantic import ValidationError

from skill_manager.errors import SkillValidationError
from skill_manager.models import Skill


class SkillValidator(ABC):
    """Public extension point for Skill-specific domain validation."""

    @abstractmethod
    def validate(self, skill: Skill) -> Skill:
        """Validate and return a normalized Skill value."""


class DefaultSkillValidator(SkillValidator):
    """Validate protocol invariants already represented by the Pydantic model."""

    def validate(self, skill: Skill) -> Skill:
        if skill.api_version != "1.0" or skill.kind != "skill":
            raise SkillValidationError("unsupported Skill protocol version or kind")
        if skill.lifecycle.state.value == "ACTIVE" and skill.governance.rejection_event_id:
            raise SkillValidationError("a rejected Skill revision cannot be active")
        return skill


def parse_skill_yaml(content: str, validator: SkillValidator) -> Skill:
    """Parse safe YAML, enforce explicit immutable identity, then validate the Skill."""
    if len(content.encode("utf-8")) > 1_000_000:
        raise SkillValidationError("Skill YAML exceeds the 1 MB document limit")
    try:
        value: Any = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise SkillValidationError("malformed Skill YAML") from error
    if not isinstance(value, dict):
        raise SkillValidationError("a Skill YAML document must be a mapping")
    if "skill_id" not in value:
        raise SkillValidationError("skill_id is required in persisted Skill YAML")
    try:
        skill = Skill.model_validate(value)
    except ValidationError as error:
        raise SkillValidationError("Skill YAML does not match protocol version 1.0") from error
    return validator.validate(skill)
