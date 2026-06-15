# Check request template

Paste this as the user message to the agent. Fill in the three blocks.
Keep the fences so the agent can tell the sections apart.

---

Please check these logs against these rules and report all compliance issues.

## Rules
```yaml
<paste the contents of your rules file here, e.g. rules/example_rules.yaml>
```

## Deterministic report (from the CLI, optional but recommended)
```json
<paste the output of:
  python -m src.checker --rules <rules> --logs <logs> --format json
here. If you don't have it, write "none" and the agent will reason from scratch.>
```

## Logs
```
<paste the log lines here, or the relevant slice. Include line numbers if you can.>
```

---

Output:
1. Issues grouped by severity (critical, error, warning, info), each with rule id,
   line number(s), expected vs found, and why it matters.
2. Any semantic / natural-language-rule issues the deterministic checker can't catch.
3. A final verdict: PASS or FAIL and the top fix.
