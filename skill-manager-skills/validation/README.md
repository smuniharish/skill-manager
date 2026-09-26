# Skill Manager Agent Skill validation

This directory documents the repeatable validation process for the canonical
Agent Skill. It is intentionally not a second runtime test suite and does not
provide a host-specific package.

The canonical distribution uses the Agent Skills `SKILL.md` format with
required `name` and `description` frontmatter.

Authoritative resources:

- [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
- [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)

## Structural validation

For every change:

1. Confirm [`../skills/skill-manager/SKILL.md`](../skills/skill-manager/SKILL.md)
   exists and starts with YAML frontmatter.
2. Confirm `name` is exactly `skill-manager`, matches the directory name,
   contains only lowercase letters and hyphens, and is at most 64 characters.
3. Confirm `description` is non-empty, at most 1024 characters, and states
   both the capability and when to activate it.
4. Confirm only `name` and `description` appear in frontmatter unless the
   current Agent Skills specification and a demonstrated host requirement
   justify more.
5. Resolve every relative Markdown target in the skill, references, and this
   directory.
6. Confirm there is one canonical `skills/skill-manager/` knowledge source
   and no Claude, Codex, Cursor, or Copilot duplicate.
7. Confirm the canonical skill and every bundled reference links to both the
   [examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
   and [documentation](https://skill-manager.readthedocs.io/en/latest/).
8. Search for stale package names, invented APIs or commands, credentials,
   private imports, and unrelated projects.

## Source-accuracy review

Review every code snippet and factual claim against its source:

| Claim area | Source of truth |
| --- | --- |
| Public imports | [`src/skill_manager/__init__.py`](https://github.com/smuniharish/skill-manager/blob/master/src/skill_manager/__init__.py) |
| Manager constructor and lifecycle methods | [`src/skill_manager/api.py`](https://github.com/smuniharish/skill-manager/blob/master/src/skill_manager/api.py) |
| Models and protocol | [`src/skill_manager/models.py`](https://github.com/smuniharish/skill-manager/blob/master/src/skill_manager/models.py) |
| Dependencies and Python support | [`pyproject.toml`](https://github.com/smuniharish/skill-manager/blob/master/pyproject.toml) |
| Public workflows and boundaries | [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/) |
| Executable integrations | [Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples) |
| Regression behavior | [`tests/`](https://github.com/smuniharish/skill-manager/tree/master/tests) |

If behavior lacks implementation, a focused test, an executable example, or
authoritative documentation, omit it rather than infer an API.

## Agent-task matrix

| Task | Activates | Grounded route | Avoids |
| --- | --- | --- | --- |
| “Add governed Skills to my LangGraph agent.” | Yes | `references/integration.md` to bundle construction and LangGraph example. | Turning Skill Manager into the graph runtime. |
| “Load Skill YAML from our database.” | Yes | Source/registry separation and public extension contracts. | Hard-coded database behavior in the package. |
| “Use semantic Skill discovery.” | Yes | Built-in semantic retriever and application-provided embeddings. | Invented vector-store or provider APIs. |
| “Require review for generated Skills.” | Yes | Policy configuration and approval/rejection lifecycle. | Bypassing feedback or mutating revisions. |
| “Regenerate after a rejection.” | Yes | Explicit parent ID plus feedback-informed revision example. | Autonomous self-improvement or automatic approval. |
| “Resolve a Skill's MCP requirements.” | Yes | Injected `MCPRuntime` and capability example. | Reimplementing MCP transport or routing. |
| “Send lifecycle events to Grafana.” | Yes | Public sink plus complete observability example. | Wrapping or replacing ecosystem telemetry. |
| “Debug why a Skill is missing from a bundle.” | Yes | Lifecycle, discovery, dependency, and capability sequence. | Guessing from name/version or suppressing errors. |
| “Build an autonomous agent runtime.” | No | State that LangChain/LangGraph/application owns execution. | Scope expansion. |
| “Store conversational memory.” | No | Use application-selected memory infrastructure. | Treating Skills or feedback as memory. |

## Repository validation

Skill-only work must pass the structural, link, and source-accuracy checks
above and a review of the resulting changes. If runtime files change, run the
project's formatter, linter, type checker, focused tests with coverage, and
strict MkDocs build.
