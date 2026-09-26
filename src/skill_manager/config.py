"""Small, immutable Skill Manager policy configuration."""

from pydantic import BaseModel, ConfigDict


class SkillManagerConfig(BaseModel):
    """Hard policy boundaries for agent-generated Skills."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_agent_skill_creation: bool = True
    require_human_approval: bool = False
