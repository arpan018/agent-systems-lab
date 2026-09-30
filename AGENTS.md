# Agent shared memory (read this first in every new chat)

This is a Python/`uv` **monorepo learning ladder** for OpenAI API work. Implementation has not started until the user says **start the implementation**.

## Bootstrap (do this before writing code)

1. Read `.cursor/rules/` (always-on rules apply automatically).
2. If present, read `Temp/openai_api_learning_project_ladder.md` (local plan; gitignored).
3. If present, read `Temp/PROGRESS.md` for current stage and blockers.
4. Do **not** skip stages or start the capstone first.
5. Do **not** extract into `src/common/` until a second project genuinely reuses the code.

## Folders

| Path | Role | Git |
|------|------|-----|
| `Temp/` | Plan, progress tracker, scaffolding notes until each project README exists | ignored |
| `Docs/` | Deep teaching notes (why each line exists, diagrams) when a stage is implemented | ignored until we publish |
| `projects/` | One folder per stage, independently runnable | tracked |
| `src/common/` | Shared utilities earned by reuse | tracked |
| `.cursor/rules/` | Instructions every new chat should follow | tracked |

## Feature size

Check the files and the code against the feature before keeping them.

- A small feature stays small. A few focused modules are enough for one call path.
- Do not collapse a real boundary into one file just to look short. Split when a second responsibility is actually there.
- Do not add files, knobs, or reports the current feature does not use.
- If a module would only hold one type or one check, keep that code in the module that uses it.
- Tests cover the behavior this feature claims. Skip hypothetical models and unused controls.

## When the user says "start the implementation"

- Implement **only the requested stage**.
- Teach in `Docs/<stage>/` with a detailed README, diagrams, and comments that explain *why*, not only *what*.
- Keep production code readable; put long tutorials in `Docs/`, not in huge inline essays.
- Each stage: short project README (setup/run/success+failure), tests for deterministic logic, no secrets in logs.

## Commands you will usually use

```bash
uv sync
uv run pytest
uv run ruff check .
```

Stage-specific run commands belong in that project's README once it exists.
