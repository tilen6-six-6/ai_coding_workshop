"""Load rules and evaluate them against parsed log entries.

A rules file is YAML (or JSON) shaped like:

    meta:
      appliance: "Acme Firewall v3"
    rules:
      - id: REQUIRE_LEVEL
        description: Every entry must have a level field
        severity: error
        type: required_fields
        fields: [level]

      - id: ALLOWED_LEVELS
        type: allowed_values
        field: level
        allowed: [DEBUG, INFO, WARN, ERROR]
        severity: warning

See rules/schema.md for every rule type and its options.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except ImportError:  # pragma: no cover
    _HAVE_YAML = False

from .models import Issue, LogEntry, Report


class RuleError(Exception):
    pass


def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith((".yaml", ".yml")):
        if not _HAVE_YAML:
            raise RuleError("PyYAML not installed; cannot read YAML rules. `pip install PyYAML`.")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict) or "rules" not in data:
        raise RuleError("Rules file must be a mapping with a top-level 'rules' list.")
    return data


# ---- helpers ---------------------------------------------------------------

def _severity(rule: Dict[str, Any]) -> str:
    return str(rule.get("severity", "error")).lower()


def _excerpt(entry: LogEntry, limit: int = 200) -> str:
    return entry.raw[:limit]


def _filter_matches(rule: Dict[str, Any], entry: LogEntry) -> bool:
    """Optional `when` filter: only apply rule to entries matching field=value."""
    when = rule.get("when")
    if not when:
        return True
    for k, v in when.items():
        if entry.get(k) != v:
            return False
    return True


# ---- individual rule type evaluators --------------------------------------
# Each returns a list of Issue for a single entry (or for the whole set).

def _eval_required_fields(rule, entry) -> List[Issue]:
    issues = []
    for fld in rule.get("fields", []):
        if fld not in entry.fields or entry.fields.get(fld) in (None, ""):
            issues.append(Issue(
                rule_id=rule["id"], severity=_severity(rule),
                message=f"Missing required field '{fld}'",
                line_no=entry.line_no, log_excerpt=_excerpt(entry),
                expected=f"field '{fld}' present", actual="absent/empty",
            ))
    return issues


def _eval_allowed_values(rule, entry) -> List[Issue]:
    fld = rule["field"]
    if fld not in entry.fields:
        return []
    allowed = rule.get("allowed", [])
    val = entry.get(fld)
    if val not in allowed:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}' has disallowed value '{val}'",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f"one of {allowed}", actual=val,
        )]
    return []


def _eval_forbidden_values(rule, entry) -> List[Issue]:
    fld = rule["field"]
    if fld not in entry.fields:
        return []
    forbidden = rule.get("forbidden", [])
    val = entry.get(fld)
    if val in forbidden:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}' has forbidden value '{val}'",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f"not one of {forbidden}", actual=val,
        )]
    return []


def _eval_range(rule, entry) -> List[Issue]:
    fld = rule["field"]
    if fld not in entry.fields:
        return []
    val = entry.get(fld)
    try:
        num = float(val)
    except (TypeError, ValueError):
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}' is not numeric, cannot range-check",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected="numeric", actual=val,
        )]
    lo = rule.get("min")
    hi = rule.get("max")
    if lo is not None and num < lo:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}'={num} below min {lo}",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f">= {lo}", actual=num,
        )]
    if hi is not None and num > hi:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}'={num} above max {hi}",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f"<= {hi}", actual=num,
        )]
    return []


def _eval_regex_match(rule, entry) -> List[Issue]:
    """Field value must match the pattern."""
    fld = rule["field"]
    if fld not in entry.fields:
        return []
    pattern = rule["pattern"]
    val = str(entry.get(fld, ""))
    if not re.search(pattern, val):
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Field '{fld}' does not match pattern",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f"match /{pattern}/", actual=val,
        )]
    return []


def _eval_forbidden_pattern(rule, entry) -> List[Issue]:
    """The raw line (or a field) must NOT contain the pattern."""
    pattern = rule["pattern"]
    target = str(entry.get(rule["field"], "")) if rule.get("field") else entry.raw
    if re.search(pattern, target):
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Forbidden pattern found: /{pattern}/",
            line_no=entry.line_no, log_excerpt=_excerpt(entry),
            expected=f"no match for /{pattern}/", actual=target[:120],
        )]
    return []


# ---- whole-dataset (aggregate) rule evaluators -----------------------------

def _eval_must_occur(rule, entries) -> List[Issue]:
    """At least `count` entries must match the `match` field=value spec."""
    match = rule.get("match", {})
    count_req = rule.get("count", 1)
    found = sum(1 for e in entries if all(e.get(k) == v for k, v in match.items()))
    if found < count_req:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Expected >= {count_req} entries matching {match}, found {found}",
            expected=f">= {count_req}", actual=found,
        )]
    return []


def _eval_must_not_occur(rule, entries) -> List[Issue]:
    """No entry may match the `match` spec (or at most `max_count`)."""
    match = rule.get("match", {})
    max_count = rule.get("max_count", 0)
    hits = [e for e in entries if all(e.get(k) == v for k, v in match.items())]
    if len(hits) > max_count:
        first = hits[0]
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Found {len(hits)} entries matching forbidden {match} (max {max_count})",
            line_no=first.line_no, log_excerpt=_excerpt(first),
            expected=f"<= {max_count}", actual=len(hits),
        )]
    return []


def _eval_ordering(rule, entries) -> List[Issue]:
    """Event `before` must appear before event `after` (by line order).

    Events identified by a field=value spec each.
    """
    before = rule.get("before", {})
    after = rule.get("after", {})
    before_line = next((e.line_no for e in entries
                        if all(e.get(k) == v for k, v in before.items())), None)
    after_line = next((e.line_no for e in entries
                       if all(e.get(k) == v for k, v in after.items())), None)
    if before_line is None or after_line is None:
        if rule.get("require_both", False):
            return [Issue(
                rule_id=rule["id"], severity=_severity(rule),
                message=f"Ordering rule needs both events; before={before_line}, after={after_line}",
            )]
        return []
    if before_line > after_line:
        return [Issue(
            rule_id=rule["id"], severity=_severity(rule),
            message=f"Event {before} (line {before_line}) occurred after {after} (line {after_line})",
            line_no=after_line,
            expected=f"{before} before {after}", actual="wrong order",
        )]
    return []


_PER_ENTRY = {
    "required_fields": _eval_required_fields,
    "allowed_values": _eval_allowed_values,
    "forbidden_values": _eval_forbidden_values,
    "range": _eval_range,
    "regex_match": _eval_regex_match,
    "forbidden_pattern": _eval_forbidden_pattern,
}

_AGGREGATE = {
    "must_occur": _eval_must_occur,
    "must_not_occur": _eval_must_not_occur,
    "ordering": _eval_ordering,
}


def evaluate(rules_doc: Dict[str, Any], entries: List[LogEntry]) -> Report:
    report = Report(entries_checked=len(entries))
    rules = rules_doc.get("rules", [])
    report.rules_evaluated = len(rules)

    for rule in rules:
        if "id" not in rule or "type" not in rule:
            raise RuleError(f"Each rule needs 'id' and 'type': {rule}")
        rtype = rule["type"]

        if rtype in _PER_ENTRY:
            fn = _PER_ENTRY[rtype]
            for entry in entries:
                if _filter_matches(rule, entry):
                    for issue in fn(rule, entry):
                        report.add(issue)
        elif rtype in _AGGREGATE:
            fn = _AGGREGATE[rtype]
            for issue in fn(rule, entries):
                report.add(issue)
        else:
            raise RuleError(f"Unknown rule type '{rtype}' in rule '{rule['id']}'")

    return report
