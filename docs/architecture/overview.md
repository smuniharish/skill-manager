# Architecture overview

Skill Manager is an async Skill-domain facade between your application and
its declarative Skill catalog. It validates and governs Skills, discovers
active candidates, resolves dependencies and capability requirements, and
returns `SkillBundle` data. Your application chooses how to present those
instructions to LangChain or LangGraph and owns their execution.

```text
LangChain / LangGraph application
        | requests Skills / consumes bundle
        v
   SkillManager (validation, policy, lifecycle, discovery, composition)
      |               |                 |
 SkillSource      SkillRegistry     external services
 (documents)   (validated catalog) (MCP, feedback, refresh)
      \               |                 /
       \--------------+----------------/
                      |
              SkillBundle data --------> application agent or graph
```

The manager uses `refresh-engine` for configured refresh operations,
`xstructured` for structured agent-generated candidates, and
`feedback-manager` for approval/rejection event records. Capability
lookup delegates to `mcp-capability-router`; execution routing stays with
that runtime. ContextSage optimizes context at the consuming application
boundary, while `langgraph-xai` instruments execution in the application's
LangGraph. None of these integrations requires LangSmith.

Choose a source for document persistence, a registry for operational
catalog behavior, and a discovery provider or retrieval/reranking stages for
search. The defaults work without external services for basic Skills.
See the [responsibility matrix](RESPONSIBILITY_MATRIX.md) and
[public API map](PUBLIC_API_MAP.md) for the contracts.
