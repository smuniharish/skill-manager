# Skill identity and revisions

Each new `Skill` receives an opaque immutable ID (`sk_` followed by 26
characters). It is independent of its human-readable name and metadata
version. `load("name")` selects an active version; `load(skill_id)` addresses
one exact revision, including a rejected revision retained for audit.

```python
from skill_manager import Skill, SkillMetadata, SkillProvenance

first = Skill(
    metadata=SkillMetadata(name="review", version="1.0", description="Review text"),
    instructions=("Review the text.",),
)
second = Skill(
    metadata=first.metadata,
    instructions=("Review the text and provide examples.",),
    revision=first.revision + 1,
    provenance=SkillProvenance(parent_skill_ids=(first.skill_id,)),
)
assert second.skill_id != first.skill_id
assert second.provenance.parent_skill_ids == (first.skill_id,)
```

Use the exact ID for `approve_skill` and `reject_skill`: a name can refer to
more than one version. Persisted Skill documents retain their ID across
loads. A revised Skill is a new record, not an in-place rewrite of the
earlier record.
