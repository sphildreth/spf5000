---
name: create-architectural-decision-record
description: 'Use when a change affects SPF5000 architecture, runtime, storage, provider boundaries, display behavior, or any accepted ADR. Creates a new ADR in `design/adr/` using the repository''s existing format and numbering.'
---

# Create Architectural Decision Record

Create a new ADR for SPF5000 when a task materially changes accepted architecture or needs a new architectural decision recorded.

## When to use this skill

Use this skill when a task changes:

- the chosen backend or frontend stack
- persistence boundaries between DecentDB and filesystem storage
- provider abstraction or sync behavior
- browser kiosk/runtime behavior on the Pi
- display rendering strategy or `/display` behavior
- authentication, security, or other major system boundaries

## Required repo context

Before drafting:

1. Read `design/ADR.md`
2. Read `design/adr/README.md`
3. Read the most relevant existing ADRs in `design/adr/`
4. Determine the next sequential 4-digit ADR number from the current files

## Output requirements

- Save the ADR under `design/adr/NNNN-title.md`
- Use the repository’s existing ADR style rather than introducing YAML frontmatter
- Use concise lowercase-hyphen filenames
- Prefer creating a new ADR that supersedes or refines earlier decisions instead of rewriting accepted ADR history

## Required ADR structure

Use this structure:

```md
# ADR NNNN: Decision Title

- Status: Proposed
- Date: YYYY-MM-DD

## Context
[Why the decision is needed, constraints, alternatives at a high level]

## Decision
[The chosen decision and why it is being made]

## Consequences
- [Positive consequence]
- [Trade-off or negative consequence]
```

## Drafting checklist

- State the decision clearly and unambiguously
- Explain the forces and constraints in `Context`
- Document both benefits and trade-offs in `Consequences`
- Reference related ADRs when helpful
- Update `design/SPEC.md`, `README.md`, or other affected docs when the ADR changes externally visible architecture
