# Governance boundary

The manager's immutable `SkillManagerConfig` sets policy, not a prompt.
Disabling agent creation rejects generation, registration and agent-origin
source records. Requiring human approval makes new agent revisions pending
until an explicit approval addressed by immutable Skill ID. Human-origin
Skills do not inherit this agent-only gate.

An imported document's claimed approval reference is not sufficient: the
manager verifies a resolved matching event with `feedback-manager`. On
approval or rejection, event processing precedes the Skill transition.
This separation prevents a document or model response from granting itself
authority over the catalog. See the [lifecycle](lifecycle.md) and
[feedback boundary](feedback-boundary.md).
