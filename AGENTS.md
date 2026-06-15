# AGENTS.md

Guidance for AI coding agents (Claude, Cursor, Copilot, etc.) working in this
repository. Humans should read `README.md` first; this file is the operational
contract for automated contributors.

## What this project is

LogInspect is a **rules-driven log reviewer** for embedded-device telemetry. It
parses timestamped device-state snapshots and checks each field against a
declarative spec, reporting anything out of specification. It was built around
a dishwasher control unit (GCU-P) but nothing in the core is device-specific —
device knowledge lives entirely in spec files and parsers, never in the engine.

## Golden rules

1. **Never hard-code device knowledge in the engine.** Limits, enum values,
   fault flags, and required keys belong in a YAML spec under `specs/`, not in
   Python. If you find yourself writing `if key == "temperature"` in
   `rules/engine.py`, stop — add a rule type or a spec entry instead.
2. **Keep the layers separate.** `parsers/` turn bytes into a `LogFile`;
   `rules/` evaluate a `LogFile`; `report/` render results. A change in one
   layer should not require changes in another.
3. **Every new capability ships with a test.** No new check type, parser, or
   renderer is "done" until `tests/` covers it. Target ≥90% coverage.
4. **The spec file is a public contract.** Changing how a check interprets its
   `params` is a breaking change. Add a new check type rather than silently
   redefining an existing one.

## Architecture map

```
src/loginspect/
  model.py          Snapshot, LogFile, Finding, Severity  (no logic, just data)
  parsers/
    base.py         BaseParser ABC + registry + autodetect
    snapshot_text.py  parser for "[timestamp]\n  key: value" logs
  rules/
    spec.py         load + validate YAML specs into RuleSpec objects
    checks.py       each check type; registered via @check("name")
    engine.py       runs enabled checks, aggregates Findings, sorts by severity
  aggregate.py      collapse repeated findings into grouped issues + counts
  report/
    renderers.py    text, collapsed text, JSON, HTML
  specgen.py        derive a starter spec from the Excel templates
  cli/main.py       argparse CLI: review / keys / formats
specs/              YAML rule specs (the "what is out of spec" definitions)
examples/           sample log + generated report
tests/              pytest suite
```

## How to extend (recipes)

### Add a new check type
1. Write a function in `rules/checks.py` decorated with `@check("my_check")`.
   Signature: `def my_check(rule: RuleSpec, log: LogFile) -> list[Finding]`.
2. Read parameters from `rule.params`; use `_require_key(rule)` if it needs a key.
3. Return one `Finding` per deviation. Set `observed` and `expected`.
4. Add a test in `tests/test_checks.py` and document it in `docs/RULES.md`.

### Add a new log format
1. Create `parsers/my_format.py` with a `BaseParser` subclass.
2. Implement `sniff(sample)` (cheap heuristic) and `parse(path) -> LogFile`.
3. Decorate the class with `@register_parser` and import it in
   `parsers/__init__.py` so it registers on import.
4. Add parser tests with a small fixture.

### Add a new report format
Add a `render_<fmt>(result)` function in `report/renderers.py`, export it in
`report/__init__.py`, and wire a `--format` choice in `cli/main.py`.

## Commands

```bash
pip install -e ".[dev]"          # install with dev + excel extras
pytest -q                         # run tests
ruff check src tests              # lint
mypy                              # type-check
loginspect review LOG --spec specs/gcu_p.yaml --collapse   # smoke test
```

## Conventions

- Python ≥3.10, type hints everywhere, `from __future__ import annotations`.
- Dataclasses with `slots=True` for data holders.
- No network access at runtime; this is an offline analysis tool.
- Findings must be deterministic and sorted (severity desc, then snapshot index).
- Do not commit real customer logs. `examples/` may hold sanitized samples only.
- Large/binary inputs (`*.xlsm`, big logs) stay out of git unless explicitly
  intended as templates; see `.gitignore`.

## Things NOT to do

- Do not add runtime dependencies beyond PyYAML without discussion. `openpyxl`
  is an optional extra used only by `specgen`, never at review time.
- Do not make the engine import from `report/` or `cli/` (dependency direction
  is model → parsers/rules → report → cli).
- Do not silently swallow rule errors; surface them in `ReviewResult.rule_errors`.
- Do not reformat unrelated files in a change.
