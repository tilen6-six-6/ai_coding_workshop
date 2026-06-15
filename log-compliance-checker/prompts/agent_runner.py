"""Reference runner: deterministic CLI report -> Claude Haiku 4.5 -> issue report.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python prompts/agent_runner.py --rules rules/example_rules.yaml --logs logs/example.log

This is a thin, dependency-light example. Adapt freely.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Make `src` importable whether run from repo root or prompts/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import parse_file          # noqa: E402
from src.rules_engine import evaluate, load_rules  # noqa: E402

MODEL = "claude-haiku-4-5"
HERE = os.path.dirname(os.path.abspath(__file__))


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True)
    ap.add_argument("--logs", required=True, nargs="+")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    try:
        from anthropic import Anthropic
    except ImportError:
        print("Install the SDK first: pip install anthropic", file=sys.stderr)
        return 2

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your environment.", file=sys.stderr)
        return 2

    # 1) deterministic pass
    rules_doc = load_rules(args.rules)
    entries = []
    for p in args.logs:
        entries.extend(parse_file(p))
    report = evaluate(rules_doc, entries)
    report_json = json.dumps(report.to_dict(), indent=2, default=str)

    # 2) build the prompt
    system_prompt = read(os.path.join(HERE, "agent_system_prompt.md"))
    rules_text = read(args.rules)
    logs_text = "\n".join(read(p) for p in args.logs)

    user_msg = (
        "Please check these logs against these rules and report all compliance "
        "issues.\n\n"
        f"## Rules\n```\n{rules_text}\n```\n\n"
        f"## Deterministic report (from the CLI)\n```json\n{report_json}\n```\n\n"
        f"## Logs\n```\n{logs_text}\n```\n\n"
        "Output: issues grouped by severity, plus any semantic issues the "
        "checker can't catch, then a final PASS/FAIL verdict and the top fix."
    )

    # 3) call Haiku 4.5
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=args.model,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    print("=== Deterministic report ===")
    print(report_json)
    print("\n=== Claude Haiku 4.5 analysis ===")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
