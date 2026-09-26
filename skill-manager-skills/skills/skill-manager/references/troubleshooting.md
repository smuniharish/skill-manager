# Debugging and testing Skill Manager

Reproduce the failure before changing configuration or application code.
Capture the exact public constructor arguments, Skill YAML or model shape,
lifecycle state, immutable Skill ID, source/registry types, and async call
that failed.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

## Investigation sequence

1. **Confirm the boundary.** Determine whether the failure belongs to Skill
   validation/lifecycle, or to LangChain, LangGraph, MCP transport, feedback
   persistence, refresh infrastructure, telemetry, or the application.
2. **Inspect the exact revision.** Use the immutable Skill ID. Do not infer
   revision identity from name or metadata version alone.
3. **Inspect lifecycle and origin.** Pending and rejected Skills are
   intentionally excluded from discovery and bundle composition.
4. **Inspect source health.** Read `manager.source_errors` after load or
   refresh failures. Healthy source data can be retained while another source
   reports an explicit error.
5. **Inspect validation input.** Confirm YAML is data, fields match protocol
   version `1.0`, metadata version is PEP 440 compatible, and dependencies and
   capabilities use supported shapes.
6. **Inspect discovery bounds.** Confirm `top_k`, exact filters, candidate-pool
   size, active catalog contents, and custom retriever/reranker outputs.
7. **Inspect dependency and capability failures.** Follow the reported
   dependency path or cycle. Confirm the injected `MCPRuntime` contains every
   required capability.
8. **Inspect governance ordering.** Feedback submission must complete before
   approval or rejection changes state. A rejected revision cannot be
   reactivated.
9. **Inspect generation.** Confirm the generator is a LangChain `Runnable`,
   xstructured produced a valid `Skill`, repair is configured deliberately,
   and parent feedback is addressed by a new revision.
10. **Inspect observability separately.** Sink errors are logged and exposed
    through `manager.observability_errors`; they do not reverse successful
    domain writes.
11. **Compare with a runnable example.** Use the closest file in the
    [example collection](https://github.com/smuniharish/skill-manager/tree/master/examples)
    and the relevant published
    [documentation](https://skill-manager.readthedocs.io/en/latest/).

## Common diagnoses

| Symptom | Verify first |
| --- | --- |
| Skill cannot be discovered | It is active, indexed, matches filters, and `top_k` is positive. |
| Bundle rejects a Skill | Every root and dependency is active and all version constraints resolve. |
| Agent Skill remains pending | Human approval is required; call `approve_skill` with its immutable ID. |
| Approved view omits an active Skill | “Approved” requires a recorded approval event; human-authored active is not synonymous with approved. |
| Rejected Skill cannot be removed | Rejected revisions are retained for auditability. |
| Capability resolution fails | Inject and populate the application's `MCPRuntime`. |
| Refresh returns errors | Inspect each source failure and the external refresh result separately. |
| Generated correction lacks lineage | Pass the rejected revision as `parent_skill_id`. |
| Custom discovery construction fails | Do not combine a complete provider with direct stages or a custom pool size. |
| Telemetry is missing | Inject a sink and inspect `observability_errors`; the default sink intentionally performs no I/O. |

## Focused verification

Adapt the smallest relevant
[example](https://github.com/smuniharish/skill-manager/tree/master/examples)
or repository test. Assert the measurable property that motivated the
change: exact state transition, preserved immutable ID, new revision lineage,
bounded result count, dependency order, capability name, bundle content,
source error, or sanitized event name.

For runtime changes, run the repository's formatter, linter, type checker,
focused tests with branch coverage, and strict documentation build. For
skill-only changes, follow
[`../../../validation/README.md`](../../../validation/README.md).
