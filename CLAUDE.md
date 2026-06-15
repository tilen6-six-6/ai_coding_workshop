# Claude Code Configuration

This repository is optimized for **Claude Haiku** — a fast, capable model ideal for this project's scope.

## Model recommendation

- **Primary model**: Claude Haiku (claude-haiku-4-5-20251001)
- **Use case**: Code review, spec writing, check implementation, test writing, documentation
- **Why Haiku**: LogInspect is a well-structured, modular codebase with clear conventions (see `AGENTS.md`). Haiku is fast and accurate for:
  - Adding new check types following the `@check()` pattern
  - Writing YAML specs and validation logic
  - Implementing parsers
  - Test-driven development

## When to use other models

- **Opus** (claude-opus-4-8): Only if working on complex multi-file refactors or architectural decisions affecting the entire system
- **Sonnet** (claude-sonnet-4-6): For larger tasks spanning multiple subsystems

## Workflows

See `AGENTS.md` for architectural guidelines, recipes for extending the system, and the golden rules that keep the codebase clean.

Run tests before pushing:
```bash
pytest -q && ruff check src tests && mypy
```
