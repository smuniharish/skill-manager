# Enforcing application-specific Skill rules

Add domain checks by implementing the public `SkillValidator` contract and
injecting the validator into the manager:

```python
from skill_manager import (
    Skill,
    SkillManager,
    SkillValidationError,
    SkillValidator,
)


class TransactionReviewValidator(SkillValidator):
    def validate(self, skill: Skill) -> Skill:
        if skill.metadata.name == "transaction-review" and not any(
            "rollback" in instruction.lower() for instruction in skill.instructions
        ):
            raise SkillValidationError("transaction-review must cover rollback")
        return skill


manager = SkillManager(validator=TransactionReviewValidator())
```

This is a focused extension excerpt, not a standalone example. Keep
application-specific rules here; retain the canonical `Skill` model and
normal source validation. A validator should return the validated Skill or
raise a meaningful `SkillValidationError`.

The deterministic
[constructor injection example](../examples/constructor-injection-matrix.md)
verifies custom validator injection among the supported manager extensions.
