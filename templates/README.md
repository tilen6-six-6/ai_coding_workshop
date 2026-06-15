# Templates

Manufacturer reference spreadsheets used as the source of truth for device
limits and naming. These are **inputs to the spec generator**, not consumed at
review time.

- `params_GCU-P_260611_7_8_0.xlsm` — parameter workbook. The `Performance`
  sheet (MIN/MAX/DEFAULT columns) drives auto-generated `range` rules. The
  `Aliases` sheet maps internal parameter names to log keys.
- `washtable_GCU-P.xlsx` — wash-program / sequence definitions, alias tables,
  program flags, and command definitions.

Regenerate a starter spec from these:

```bash
python -m loginspect.specgen \
  --params templates/params_GCU-P_260611_7_8_0.xlsm \
  --washtable templates/washtable_GCU-P.xlsx \
  --out specs/gcu_p.generated.yaml
```

Generated rules with `enabled: false` need a verified key mapping before use.
Always review generated output against the hand-curated `specs/gcu_p.yaml`.
