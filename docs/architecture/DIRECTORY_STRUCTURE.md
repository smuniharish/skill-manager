# Documentation map

Start with the [architecture overview](overview.md) for the Skill domain
boundary. The [responsibility matrix](RESPONSIBILITY_MATRIX.md) answers who
owns each operation; [architecture decisions](ARCHITECTURE_DECISIONS.md)
explain the tradeoffs. The [public API map](PUBLIC_API_MAP.md) identifies
supported extension points. Use [dependency boundaries](dependency-boundaries.md)
and the [dependency matrix](DEPENDENCY_MATRIX.md) when integrating external
libraries.

For application work, begin with [Skills](../concepts/skills.md), then choose
the pages relevant to your workflow: [sources](../concepts/skill-sources.md),
[registry](../concepts/registry.md),
[discovery](../concepts/discovery.md),
[bundles](../concepts/skill-bundles.md), and
[governance](../concepts/governance.md). The public API reference and
examples complement these conceptual pages.

Skill Manager owns the Skill domain. Applications and the ecosystem own
model/provider selection, graph execution, MCP routing, refresh
infrastructure, feedback storage and execution provenance. The design does
not require LangSmith.
