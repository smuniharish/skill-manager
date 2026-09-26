# Dependency boundaries

Skill Manager integrates other libraries through their public APIs rather
than rebuilding their runtimes. The [dependency matrix](DEPENDENCY_MATRIX.md)
records releases and API facts verified on 2026-09-26. Declared constraints
currently restrict this package to Python 3.12.

| At the Skill boundary | External owner |
|---|---|
| Validate a generated candidate and enforce governance | `xstructured` extracts structured model output from an application `Runnable` |
| Resolve a required capability by name | `mcp-capability-router` discovers and executes MCP operations |
| Refresh catalog data after resource changes | `refresh-engine` plans and performs configured refresh work |
| Record Skill-specific origin and parent IDs | `langgraph-xai` instruments application graph execution |
| Decide whether a Skill can be approved or rejected | `feedback-manager` persists and processes the decision event |
| Return instructions in a bundle | LangChain/LangGraph application runs its own model/agent |

ContextSage can preserve application context; it does not edit a resolved
bundle or enforce Skill governance. Dependency errors become Skill-domain
errors only where the manager's public operation needs that contract; the
external owner otherwise retains its own failure semantics. Neither
LangSmith nor external credentials are required for a basic Skill workflow.
