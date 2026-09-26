# Agent Skills

Skill Manager publishes one portable Agent Skill that teaches coding agents
how to integrate, configure, extend, debug, and test the existing
`skill-manager` package. It is procedural developer guidance; it is not a
runtime YAML Skill and does not change how the Python package is installed.

| Component | Location |
| --- | --- |
| Skill Manager Python runtime | [`src/skill_manager/`](https://github.com/smuniharish/skill-manager/tree/master/src/skill_manager) |
| Canonical Agent Skill | [`skill-manager-skills/skills/skill-manager/`](https://github.com/smuniharish/skill-manager/tree/master/skill-manager-skills/skills/skill-manager) |
| Canonical instructions | [`SKILL.md`](https://github.com/smuniharish/skill-manager/blob/master/skill-manager-skills/skills/skill-manager/SKILL.md) |

The skill follows the [Agent Skills specification](https://agentskills.io/specification)
and contains only the required `name` and `description` frontmatter. There is
no separate Claude, Codex, Cursor, or Copilot copy.

The skill always directs agents to the authoritative
[Skill Manager examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
and [Skill Manager documentation](https://skill-manager.readthedocs.io/en/latest/).

## Install from skills.sh

Install the canonical skill directory directly:

```bash
npx skills add https://github.com/smuniharish/skill-manager/tree/master/skill-manager-skills/skills/skill-manager
```

Follow the CLI's current target-selection prompts, then verify that it placed
the complete `skill-manager` folder in the selected agent's supported skills
directory.

## Install manually

Obtain the canonical directory from the
[repository](https://github.com/smuniharish/skill-manager/tree/master/skill-manager-skills/skills/skill-manager).
Copy the complete `skill-manager` directory, including `SKILL.md` and
`references/`, into a location supported by the host.

### Claude Code

| Scope | Destination |
| --- | --- |
| Current repository | `.claude/skills/skill-manager/` |
| All local projects | `~/.claude/skills/skill-manager/` |

Restart or reload Claude Code after copying the directory. Invoke the skill
explicitly with `/skill-manager` when needed. See
[Claude Code Skills](https://code.claude.com/docs/en/skills).

### Codex

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/skill-manager/` |
| All local projects | `~/.agents/skills/skill-manager/` |

Codex can discover the skill from its description or invoke it explicitly as
`$skill-manager`. See
[ChatGPT and Codex Skills](https://learn.chatgpt.com/docs/build-skills).

### Cursor

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/skill-manager/` or `.cursor/skills/skill-manager/` |
| All local projects | `~/.agents/skills/skill-manager/` or `~/.cursor/skills/skill-manager/` |

Restart Cursor after copying the directory, then select `skill-manager` from
the Agent chat skill menu. See
[Cursor Agent Skills](https://cursor.com/docs/skills).

### GitHub Copilot

| Scope | Destination |
| --- | --- |
| Current repository | `.agents/skills/skill-manager/`, `.github/skills/skill-manager/`, or `.claude/skills/skill-manager/` |
| All local projects | `~/.agents/skills/skill-manager/` or `~/.copilot/skills/skill-manager/` |

Start a new Copilot CLI session or reload skills, then verify that
`skill-manager` is available. See
[Adding agent skills for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).

### Other compatible hosts

Copy the complete canonical directory to the host's documented Agent Skills
location. Add a thin host adapter only if the host requires metadata; never
duplicate the instructions.

## Verify

After installation, confirm:

1. The directory name is `skill-manager`.
2. `SKILL.md` and `references/` are present.
3. The host lists `skill-manager`, when it provides a skill listing UI or
   command.
4. A task about Skill registration, discovery, bundles, governance, or
   LangGraph integration activates the skill.
5. The skill links to the current
   [examples](https://github.com/smuniharish/skill-manager/tree/master/examples)
   and [documentation](https://skill-manager.readthedocs.io/en/latest/).

See the distribution
[README](https://github.com/smuniharish/skill-manager/blob/master/skill-manager-skills/README.md)
and
[validation process](https://github.com/smuniharish/skill-manager/blob/master/skill-manager-skills/validation/README.md)
for maintenance details.
