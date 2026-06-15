# Log Compliance Checker

Takes in **logs** and **rule files** describing how an appliance/system *should* behave and how its logs *should* look. It checks each log entry against the rules and flags any **issues** where logs don't match the rules.

Designed to be:
- Run locally via CLI (deterministic checks, no AI needed)
- Connected to a **Claude Haiku 4.5 agent** for fuzzy/semantic checks and human-readable issue explanations

## How it works

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  logs/   │────▶│  Parser      │────▶│ Rule Engine │────▶│ Issues   │
│ rules/   │     │ (normalize)  │     │ (match)     │     │ report   │
└──────────┘     └──────────────┘     └─────────────┘     └──────────┘
                                              │
                                              ▼ (optional)
                                       ┌─────────────┐
                                       │ Claude Haiku │  semantic checks
                                       │   4.5 agent  │  + explanations
                                       └─────────────┘
```

1. **Parser** reads logs (JSON, JSONL, plain text, syslog) and normalizes each entry into a common shape.
2. **Rule Engine** loads rules (YAML/JSON) and evaluates each log entry. Rules can assert required fields, allowed values, value ranges, ordering, presence/absence of events, rate limits, and forbidden patterns.
3. **Issues report** lists every violation with severity, the offending log line, and which rule failed.
4. **Claude agent** (optional) handles checks too fuzzy for hard rules and writes plain-English explanations of issues.

## Quick start

```bash
pip install -r requirements.txt

# Run the deterministic checker
python -m src.checker --rules rules/example_rules.yaml --logs logs/example.log

# Output issues as JSON
python -m src.checker --rules rules/example_rules.yaml --logs logs/example.log --format json --out report.json
```

## Connecting the Claude Haiku 4.5 agent

This repo is built so you can connect it to a Claude agent (Haiku 4.5). The agent reads:
- `prompts/agent_system_prompt.md` — the agent's instructions
- The deterministic report from the CLI (so the model doesn't re-do work code can do reliably)

See `prompts/` for ready-to-paste prompts and `prompts/AGENT_SETUP.md` for wiring it up.

## Repo layout

```
log-compliance-checker/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── checker.py         # CLI entry point
│   ├── parser.py          # log parsing/normalization
│   ├── rules_engine.py    # rule loading + evaluation
│   └── models.py          # shared data types
├── rules/
│   ├── example_rules.yaml # human-friendly rule format
│   └── schema.md          # rule format reference
├── logs/
│   └── example.log        # sample logs (some passing, some failing)
├── prompts/
│   ├── agent_system_prompt.md
│   ├── check_request_template.md
│   └── AGENT_SETUP.md
├── tests/
│   └── test_rules_engine.py
└── .github/workflows/
    └── ci.yml
```

## License
MIT
