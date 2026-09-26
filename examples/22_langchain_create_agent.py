"""Run a SkillBundle through LangChain create_agent and LangGraph."""

from __future__ import annotations

import asyncio
import json

from _agent_common import (
    bundle_system_prompt,
    configured_model,
    final_text,
    incident_review_bundle,
)
from langchain.agents import create_agent
from langchain.tools import tool


@tool
def get_incident_record(incident_id: str) -> str:
    """Return the authoritative record for an incident ID."""
    if incident_id != "INC-42":
        return json.dumps({"error": "incident not found", "incident_id": incident_id})
    return json.dumps(
        {
            "incident_id": "INC-42",
            "status": "monitoring",
            "owner": "payments-platform",
        }
    )


async def main() -> None:
    bundle = await incident_review_bundle()
    agent = create_agent(
        model=configured_model(),
        tools=[get_incident_record],
        system_prompt=bundle_system_prompt(bundle),
    )
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Review INC-42. Return one sentence with its exact " "status and owner."
                    ),
                }
            ]
        }
    )
    answer = final_text(result)
    assert "monitoring" in answer.lower()
    assert "payments-platform" in answer.lower()
    print(f"runtime={type(agent).__name__}")
    print(f"skills={[skill.metadata.name for skill in bundle.skills]}")
    print(f"answer={answer}")


if __name__ == "__main__":
    asyncio.run(main())
