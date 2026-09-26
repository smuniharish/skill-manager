# Skill Manager Agent Skills

This directory is the canonical Agent Skills distribution for Skill Manager.
It contains procedural guidance for coding agents that need to integrate,
configure, test, or debug the existing `skill-manager` package.

It is not a Python package, a runtime Skill catalog, or a replacement for
Skill Manager's canonical YAML Skill protocol.

| Component | Location | Purpose |
| --- | --- | --- |
| Skill Manager runtime | [`src/skill_manager/`](https://github.com/smuniharish/skill-manager/tree/master/src/skill_manager) | The published Python package and its supported public API. |
| Skill Manager Agent Skill | [`skills/skill-manager/`](skills/skill-manager/) | Canonical agent-oriented instructions and concise reference material. |
| Skill validation | [`validation/`](validation/) | Structural validation and a realistic activation/task matrix. |

## Agent Skills format

The canonical skill follows the Agent Skills `SKILL.md` format: a
directory-scoped Markdown instruction file with required `name` and
`description` YAML frontmatter. Its `name` matches its containing directory
(`skill-manager`), and only the specification's required frontmatter is used
for portability.

Compatible agents should load
[`skills/skill-manager/SKILL.md`](skills/skill-manager/SKILL.md) when working
on Skill Manager integrations, Skill lifecycle governance, discovery,
composition, or extension points. The skill uses the authoritative
[Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/)
and [executable examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
instead of maintaining a second product manual.

For skills.sh, Claude Code, Codex, Cursor, GitHub Copilot, and manual
installation instructions, see
[Agent Skills - Skill Manager](https://skill-manager.readthedocs.io/en/latest/agent-skills/).
This repository intentionally provides one portable skill instead of
platform-specific copies.

## Maintaining the distribution

When Skill Manager's public API, integrations, or documented behavior changes:

1. Update the canonical skill and only the affected reference material.
2. Verify every claim against the public API, tests, the
   [examples](https://github.com/smuniharish/skill-manager/tree/master/examples),
   or the
   [published documentation](https://skill-manager.readthedocs.io/en/latest/).
3. Run the process in [`validation/README.md`](validation/README.md).
4. Do not add platform-specific copies of the skill text. Add thin metadata
   only when a host's current official documentation requires it.

The distribution is covered by the repository's Apache License 2.0; see the
[repository license](https://github.com/smuniharish/skill-manager/blob/master/LICENSE).
