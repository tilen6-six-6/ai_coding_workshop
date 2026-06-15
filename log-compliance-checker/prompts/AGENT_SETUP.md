# Connecting a Claude Haiku 4.5 agent to this repo

You have two easy paths. Both use the files already in this repo.

## Option A — Claude app / Project (no code)

1. Create a new Project (or Custom Agent) in the Claude app.
2. Set the **model to Claude Haiku 4.5**.
3. Paste `prompts/agent_system_prompt.md` into the project's custom instructions.
4. Add this whole GitHub repo as **project knowledge** (connect the repo, or
   upload `rules/`, `logs/`, and `prompts/`).
5. To run a check, send the agent the filled-in `prompts/check_request_template.md`.
   For best results, first run the CLI and paste its JSON report into that template.

## Option B — Script it with the API (Haiku 4.5)

`agent_runner.py` (below, also saved next to this file) runs the deterministic
CLI, then sends its report + the rules + the logs to Claude Haiku 4.5 using the
system prompt in this folder.

```bash
pip install -r ../requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python prompts/agent_runner.py --rules rules/example_rules.yaml --logs logs/example.log
```

The model string is `claude-haiku-4-5`. (Check the docs for the exact dated
string if you pin versions.)

## Recommended flow

```
CLI (deterministic, free, exact)  ─┐
                                   ├─▶  Claude Haiku 4.5  ─▶  human-readable
rules + logs (raw, for context) ──┘     (semantic checks +    issue report
                                          explanations)
```

Let code do what code does well (ranges, required fields, patterns, counts,
ordering). Let Haiku do the fuzzy parts (intent, contradictions, natural-language
rules) and the explaining. That keeps token cost and latency low and results
reliable.
