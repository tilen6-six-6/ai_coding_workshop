# Rule format reference

A rules file is **YAML** or **JSON** with a top-level `rules` list. Each rule
needs an `id` and a `type`. Optional on every rule:

| key         | meaning                                                        |
|-------------|----------------------------------------------------------------|
| `description` | human note, shown nowhere critical                           |
| `severity`  | `info` \| `warning` \| `error` \| `critical` (default `error`)  |
| `when`      | mapping `field: value`; rule only applies to matching entries  |

`severity` decides the CLI exit code via `--fail-on`. `error` and `critical`
make `Report.passed` false.

---

## Per-entry rule types

These run once per log entry.

### `required_fields`
Entry must contain every listed field (non-empty).
```yaml
- id: REQ
  type: required_fields
  fields: [level, message]
```

### `allowed_values`
If `field` is present, its value must be in `allowed`.
```yaml
- id: LEVELS
  type: allowed_values
  field: level
  allowed: [DEBUG, INFO, WARN, ERROR]
```

### `forbidden_values`
If `field` is present, its value must NOT be in `forbidden`.
```yaml
- id: NODEBUG
  type: forbidden_values
  field: level
  forbidden: [DEBUG]
```

### `range`
`field` must be numeric and within `min`/`max` (either bound optional).
```yaml
- id: TEMP
  type: range
  field: temp_c
  min: 0
  max: 85
```

### `regex_match`
`field`'s value must match `pattern` (Python regex, `re.search`).
```yaml
- id: TS
  type: regex_match
  field: timestamp
  pattern: '^\d{4}-\d{2}-\d{2}'
```

### `forbidden_pattern`
`pattern` must NOT appear. Checks the whole raw line, or a `field` if given.
```yaml
- id: SECRETS
  type: forbidden_pattern
  pattern: '(?i)password\s*[=:]\s*\S+'
```

---

## Aggregate / sequence rule types

These run once over the whole set of entries.

### `must_occur`
At least `count` (default 1) entries must match the `match` field/value map.
```yaml
- id: STARTUP
  type: must_occur
  match: { event: startup }
  count: 1
```

### `must_not_occur`
At most `max_count` (default 0) entries may match `match`.
```yaml
- id: NOAUTHFAIL
  type: must_not_occur
  match: { event: unauthorized_access }
  max_count: 0
```

### `ordering`
The `before` event must appear before the `after` event (by line order).
Set `require_both: true` to flag an issue if either event is missing.
```yaml
- id: AUTHFIRST
  type: ordering
  before: { event: auth_ok }
  after:  { event: resource_access }
  require_both: false
```

---

## Adding a new rule type

1. Write `_eval_<name>(rule, entry)` (per-entry) or `_eval_<name>(rule, entries)`
   (aggregate) in `src/rules_engine.py`, returning a list of `Issue`.
2. Register it in `_PER_ENTRY` or `_AGGREGATE`.
3. Document it here.
