# LogInspect

A rules-driven log reviewer for embedded-device telemetry. Feed it a log and a
spec; it tells you everything that is out of specification.

LogInspect parses timestamped device-state snapshots and checks every field
against a declarative set of rules — numeric ranges, allowed enum values, fault
flags, error counters, required fields, and rate-of-change limits. It was built
around a dishwasher control unit, but the engine knows nothing about any
specific device: all device knowledge lives in spec files.

## Why

Embedded logs are huge and repetitive — thousands of near-identical snapshots,
hundreds of fields each. Eyeballing them for out-of-spec values does not scale.
LogInspect turns "is anything wrong in this log?" into a one-command answer, and
turns your hardware/firmware limits into a versioned, reviewable artifact.

## Install

```bash
pip install -e ".[dev]"        # from a clone, with dev + excel extras
# or, runtime only:
pip install -e .
```

Requires Python 3.10+. The only runtime dependency is PyYAML. `openpyxl` is an
optional extra used only by the spec generator.

## Quick start

```bash
# Review a log against a spec (human-readable, repeats collapsed)
loginspect review mylog.txt --spec specs/gcu_p.yaml --collapse

# Machine-readable output for CI / dashboards
loginspect review mylog.txt --spec specs/gcu_p.yaml --format json -o result.json

# A shareable HTML report
loginspect review mylog.txt --spec specs/gcu_p.yaml --format html -o report.html

# Explore: what telemetry keys does this log contain?
loginspect keys mylog.txt
```

Exit code is non-zero when findings reach the `--fail-on` severity (default
`error`), so it drops straight into CI.

## How it works

```
log file ──parser──▶ LogFile (snapshots) ──engine + spec──▶ Findings ──renderer──▶ text / json / html
```

1. A **parser** turns the raw file into a `LogFile` (an ordered list of
   `Snapshot`s, each a `{key: value}` map with a timestamp).
2. The **engine** runs every enabled rule in the **spec** against the log.
3. Each rule uses a **check type** (`range`, `enum`, `forbidden_value`,
   `required_keys`, `nonzero_counter`, `delta_limit`) — see `docs/RULES.md`.
4. A **renderer** formats the findings. Repeated findings can be collapsed into
   distinct issues with counts and snapshot spans.

## Writing a spec

Specs are YAML. A minimal rule:

```yaml
name: my-device
version: "1.0"
rules:
  - id: water_temp_range
    check: range
    key: temperature
    severity: warning
    description: Water temperature must stay within the ADC range.
    params: { min: 0, max: 9000 }

  - id: no_service_error
    check: forbidden_value
    key: service_status
    severity: error
    params: { values: [ERROR, FAULT] }
```

See `specs/gcu_p.yaml` for a complete worked example and `docs/RULES.md` for
every check type and its parameters.

## Generating a spec from Excel templates

If your limits live in a spreadsheet (e.g. a Performance sheet with MIN/MAX
columns), bootstrap a spec automatically:

```bash
python -m loginspect.specgen \
  --params params_GCU-P.xlsm \
  --washtable washtable_GCU-P.xlsx \
  --out specs/gcu_p.generated.yaml
```

Generated rules that need a verified key mapping are emitted with
`enabled: false` — review and enable them by hand. **Always review generated
specs before trusting them.**

## Supported log format

Out of the box, the `snapshot-text` parser handles logs shaped like:

```
[2026-06-11 15:25:55.003]
  main_sw: DW5060-GCU-P_MAIN
  service_status: OK
  temperature: 3698
  ...

[2026-06-11 15:25:56.003]
  ...
```

Adding a new format is a small, self-contained parser class — see `AGENTS.md`.

## Development

```bash
pytest -q            # tests
ruff check src tests # lint
mypy                 # types
```

## License

MIT — see `LICENSE`.
