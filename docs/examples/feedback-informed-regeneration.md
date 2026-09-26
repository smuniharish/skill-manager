# Regenerate a rejected Skill with reviewer feedback

This service-dependent example demonstrates an application-controlled
correction loop. It does not regenerate automatically when a reviewer rejects
a Skill:

```text
generate candidate
        ↓
reviewer rejects with correction notes
        ↓
application requests a new revision with parent_skill_id
        ↓
new revision remains pending for another human decision
```

## Public API example

This complete program mirrors the lifecycle in the runnable example. Set the
provider environment variables described below before running it. The
application reads credentials from its environment, not from Skill data.

```python
import asyncio
import os

from feedback_manager import (
    FeedbackCategory,
    FeedbackManager,
    FeedbackQuery,
    FeedbackStatus,
)
from langchain_openai import ChatOpenAI
from skill_manager import SkillManager, SkillManagerConfig


async def main() -> None:
    api_key = os.getenv("EXPLABS_API_KEY") or os.getenv("SKILL_MANAGER_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Configure a model API key in the process environment")
    model = ChatOpenAI(
        model=os.environ["SKILL_MANAGER_MODEL"],
        base_url=os.environ["SKILL_MANAGER_LLM_BASE_URL"],
        api_key=api_key,
        temperature=0,
    )
    feedback_manager = FeedbackManager()
    manager = SkillManager(
        config=SkillManagerConfig(
            allow_agent_skill_creation=True,
            require_human_approval=True,
        ),
        feedback_manager=feedback_manager,
    )
    first = await manager.generate_skill(
        model,
        "Create exactly one Skill named transaction-review version 1.0.0. "
        "Its only instruction must verify that the commit boundary is explicit.",
        repair_generator=model,
    )
    rejected = await manager.reject_skill(
        first.skill_id,
        feedback=(
            "Add explicit rollback verification and isolation-level checks. "
            "Keep the commit-boundary check."
        ),
        metadata={"reviewer": "database-owner", "severity": "high"},
    )
    events = await feedback_manager.query(
        FeedbackQuery(
            category=FeedbackCategory.REJECTION,
            target_type="skill",
            target_id=rejected.skill_id,
            status=FeedbackStatus.REJECTED,
        )
    )
    assert len(events) == 1
    assert events[0].payload["feedback"].startswith("Add explicit rollback verification")

    revised = await manager.generate_skill(
        model,
        "Regenerate transaction-review as version 1.1.0. Address every "
        "previous human rejection note explicitly while retaining the "
        "original valid instruction. Create a new canonical Skill ID.",
        parent_skill_id=rejected.skill_id,
        repair_generator=model,
    )
    assert revised.skill_id != rejected.skill_id
    assert revised.revision == rejected.revision + 1
    assert revised.provenance.parent_skill_ids == (rejected.skill_id,)
    assert revised.lifecycle.state.value == "PENDING_APPROVAL"
    revised_text = " ".join(revised.instructions).lower()
    assert all(term in revised_text for term in ("commit", "rollback", "isolation"))

    approved = await manager.approve_skill(
        revised.skill_id,
        metadata={
            "reviewer": "database-owner",
            "reason": "All requested corrections are present.",
        },
    )
    print(f"final_state={approved.lifecycle.state.value}")


asyncio.run(main())
```

## Run

Configure `EXPLABS_API_KEY` or `SKILL_MANAGER_LLM_API_KEY`,
`SKILL_MANAGER_LLM_BASE_URL`, and `SKILL_MANAGER_MODEL` in the process
environment or a secret manager before running the example. Do not put
credential values in command history, source files, or Skill data.

```console
uv run --extra openai-compatible python examples/24_feedback_informed_regeneration.py
```

## Verified result

The previously verified hosted-model run asserted that:

- one rejected feedback event is available for the parent revision;
- the replacement has a new immutable Skill ID and incremented revision;
- the replacement records the rejected parent ID;
- reviewer-requested commit, rollback, and isolation checks are present;
- the replacement remains `PENDING_APPROVAL` until explicit approval.

The hosted model's wording and generated IDs vary between runs. The
recorded run ended with:

```text
final_state=ACTIVE
```

This final state follows the example's explicit reviewer approval; generation
alone does not activate the replacement. For lifecycle details, see the
[rejection feedback guide](../guides/rejection-feedback.md).
