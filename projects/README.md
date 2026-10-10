# Projects

> [!IMPORTANT]
> **Human-Facing Documentation Only**: This README is maintained strictly for human developers and repository visitors. Autonomous AI agents MUST NOT ingest or utilize `README.md` files for operational instructions or context. All agent directives and navigation reside strictly in [`AGENTS.md`](./AGENTS.md) and [`routing/`](../routing/).

Initiative specs live directly in flat slug folders (`projects/<slug>/README.md`) with YAML frontmatter denoting status. Human-requested notes that are not specs live under [`notes/`](./notes/). Follow-up prompts live under [`project-prompts/`](./project-prompts/).

| Path | Use |
| --- | --- |
| [`notes/`](./notes/) | Human-requested notes (not proposals / not slug specs) |
| [`project-prompts/`](./project-prompts/) | Lean follow-up prompts for human-initiated agent runs |

## Spec skeleton (`README.md` inside a slug)

```markdown
---
status: proposed # active | ongoing | completed
owner: router
repos: [financial-advisement-router]
---

# <Project name>

## Intent
## Current state
## Completed work
## Plan / next actions
## Exit criteria
## Risks & mitigations
## Related repos & paths
## Research & results pointers
## Decisions (links to docs/)
## Open questions
```
