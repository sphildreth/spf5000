---
description: 'Conventions for maintaining SPF5000 custom agents, instructions, skills, and MCP config so they stay portable and useful across GitHub Copilot, Copilot CLI, and Opencode.'
applyTo: 'AGENTS.md,.github/agents/**/*.agent.md,.github/instructions/**/*.instructions.md,.github/skills/**/SKILL.md,.vscode/mcp.json'
---

# Agent Asset Conventions

## General rules

- Keep agent-facing assets repository-specific and high-signal.
- Prefer compact, focused assets over giant generic boilerplate.
- Use lowercase-hyphen file and folder names for `.agent.md` files, instruction files, and skill directories.
- Keep bundled skill assets local to the skill folder and reference them with relative paths.

## Custom agent files

- Every `.agent.md` file must include YAML frontmatter with at least a `description`.
- Prefer adding a human-readable `name`.
- Scope each agent to a single domain such as backend, frontend, or ADR/design work.
- Put durable repo knowledge in the agent body: architecture boundaries, validation expectations, and important file paths.

## Instruction files

- Every `.instructions.md` file must include `description` and `applyTo` frontmatter.
- Keep instruction files concise and practical.
- Use instruction files for durable repo rules, not task-specific plans or temporary notes.

## Skills

- Every skill lives under `.github/skills/<skill-name>/` and must contain `SKILL.md`.
- `SKILL.md` frontmatter must include `name` and a discovery-friendly `description`.
- The description should say what the skill does and when to use it so agents can auto-select it.
- Keep skill bodies workflow-oriented and reference any bundled assets explicitly.

## MCP config

- Keep `.vscode/mcp.json` valid JSON.
- Prefer MCP servers that directly help work in this repository.
- Prefer local stdio servers launched with stable commands such as `npx -y ...`.
- If a new MCP server changes workflow assumptions, also update `AGENTS.md` and `.github/copilot-instructions.md`.
