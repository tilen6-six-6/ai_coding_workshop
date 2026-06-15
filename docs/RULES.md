# Rule reference

A spec is a YAML file with top-level `name`, `version`, and a `rules` list.
Every rule shares these fields:

| Field         | Required | Description                                                        |
|---------------|----------|--------------------------------------------------------------------|
| `id`          | yes      | Unique identifier for the rule (used in findings and output).      |
| `check`       | yes      | The check type (see below).                                        |
| `severity`    | no       | `info`, `warning`, `error`, or `critical`. Default `warning`.      |
| `key`         | depends  | The telemetry key to inspect. Required by most checks.             |
| `description` | no       | Human-readable explanation, shown in reports.                      |
| `params`      | depends  | Check-specific parameters (see below).                             |
| `enabled`     | no       | Set `false` to keep a rule in the file but skip it. Default `true`.|

Severity ordering (worst first): `critical` > `error` > `warning` > `info`.
A review **fails** (non-zero exit) when any finding reaches `--fail-on`
(default `error`).

---

## `range`

Numeric value must fall within `[min, max]`, inclusive. Either bound may be
omitted for a one-sided check. Non-numeric values are skipped.

```yaml
- id: water_temp_range
  check: range
  key: temperature
  severity: warning
  params: { min: 0, max: 9000 }
```

Emits one finding per snapshot whose value is out of range.

---

## `enum`

Value must be one of an allowed set of strings.

```yaml
- id: diverter_state_known
  check: enum
  key: diverter_state
  severity: warning
  params:
    allowed: [POS_0, POS_1, POS_2, POS_3, MOVING, UNDEF]
```

Emits one finding per snapshot whose value is not in `allowed`.

---

## `forbidden_value`

Flags whenever a key takes one of a set of bad values — fault flags, error
states, etc. The inverse of `enum`.

```yaml
- id: no_active_faults
  check: forbidden_value
  key: bldc_status_stmcsdk_faults_active
  severity: error
  params:
    values: [OVER_VOLT, OVER_CURRENT, OVER_TEMP]
```

---

## `required_keys`

Each listed key must appear at least once anywhere in the log. Good for
catching truncated or wrong-device logs. Does not use the rule-level `key`.

```yaml
- id: core_keys_present
  check: required_keys
  severity: error
  params:
    keys: [main_sw, service_state, service_status, temperature]
```

Emits one finding per missing key (global, no snapshot index).

---

## `nonzero_counter`

Flags if a counter ever exceeds a threshold (default `0`). Reports the single
worst (highest) observation, so a climbing error counter yields one finding,
not thousands.

```yaml
- id: veeprom_errors
  check: nonzero_counter
  key: veeprom_error_cntr
  severity: error
  params: { threshold: 0 }
```

---

## `delta_limit`

Flags if the change between consecutive samples of a key exceeds `max_delta`.
Useful for detecting sensor glitches or implausible jumps.

```yaml
- id: temp_no_spikes
  check: delta_limit
  key: temperature
  severity: warning
  params: { max_delta: 2000 }
```

---

## Collapsing repeated findings

A persistent condition (e.g. a fault flag stuck on for the whole run) produces
one finding per snapshot. The `--collapse` flag (text format) and the HTML
report group findings by `(rule_id, key)` and show a count plus the span of
snapshots and timestamps the condition covered. JSON output is always the full,
uncollapsed list so downstream tools can aggregate as they wish.

## Adding your own check type

See `AGENTS.md` → "Add a new check type". In short: write a function in
`src/loginspect/rules/checks.py` decorated with `@check("name")`, returning a
list of `Finding`s, then document it here and add a test.
