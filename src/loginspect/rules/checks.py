"""Check implementations.

A check is a callable ``check(rule, log) -> list[Finding]``. New check types
register themselves in ``CHECK_TYPES`` via the ``@check`` decorator, so adding a
capability never requires editing the engine.
"""

from __future__ import annotations

from collections.abc import Callable

from loginspect.model import Finding, LogFile
from loginspect.rules.spec import RuleSpec

CheckFn = Callable[[RuleSpec, LogFile], list[Finding]]
CHECK_TYPES: dict[str, CheckFn] = {}


def check(name: str) -> Callable[[CheckFn], CheckFn]:
    def deco(fn: CheckFn) -> CheckFn:
        CHECK_TYPES[name] = fn
        return fn

    return deco


def _require_key(rule: RuleSpec) -> str:
    if not rule.key:
        raise ValueError(f"Rule {rule.id!r} ({rule.check}) requires a 'key'.")
    return rule.key


@check("range")
def check_range(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Numeric value must fall within [min, max] (inclusive). Either bound
    may be omitted for a one-sided check."""
    key = _require_key(rule)
    lo = rule.params.get("min")
    hi = rule.params.get("max")
    findings: list[Finding] = []
    for snap in log.snapshots:
        val = snap.as_float(key)
        if val is None:
            continue
        if (lo is not None and val < lo) or (hi is not None and val > hi):
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    key=key,
                    message=f"{key}={val:g} outside range [{lo}, {hi}]",
                    snapshot_index=snap.index,
                    raw_timestamp=snap.raw_timestamp,
                    observed=val,
                    expected={"min": lo, "max": hi},
                )
            )
    return findings


@check("enum")
def check_enum(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Value must be one of an allowed set of strings."""
    key = _require_key(rule)
    allowed = {str(v) for v in rule.params.get("allowed", [])}
    findings: list[Finding] = []
    for snap in log.snapshots:
        val = snap.get(key)
        if val is None:
            continue
        if val not in allowed:
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    key=key,
                    message=f"{key}={val!r} is not an allowed value",
                    snapshot_index=snap.index,
                    raw_timestamp=snap.raw_timestamp,
                    observed=val,
                    expected=sorted(allowed),
                )
            )
    return findings


@check("forbidden_value")
def check_forbidden_value(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Flag whenever a key takes one of a set of bad values (e.g. fault flags
    like ``UNDER_VOLT`` or status ``ERROR``)."""
    key = _require_key(rule)
    bad = {str(v) for v in rule.params.get("values", [])}
    findings: list[Finding] = []
    for snap in log.snapshots:
        val = snap.get(key)
        if val is not None and val in bad:
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    key=key,
                    message=f"{key} reported fault value {val!r}",
                    snapshot_index=snap.index,
                    raw_timestamp=snap.raw_timestamp,
                    observed=val,
                    expected=f"not in {sorted(bad)}",
                )
            )
    return findings


@check("required_keys")
def check_required_keys(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Each listed key must appear at least once in the log."""
    required = {str(k) for k in rule.params.get("keys", [])}
    present = log.keys
    missing = sorted(required - present)
    findings: list[Finding] = []
    for key in missing:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                key=key,
                message=f"Required key {key!r} never appears in the log",
                observed=None,
                expected="present",
            )
        )
    return findings


@check("nonzero_counter")
def check_nonzero_counter(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Flag if an error/fault counter ever exceeds a threshold (default 0)."""
    key = _require_key(rule)
    threshold = rule.params.get("threshold", 0)
    findings: list[Finding] = []
    worst = None
    worst_snap = None
    for snap in log.snapshots:
        val = snap.as_int(key)
        if val is None:
            continue
        if val > threshold and (worst is None or val > worst):
            worst, worst_snap = val, snap
    if worst_snap is not None:
        findings.append(
            Finding(
                rule_id=rule.id,
                severity=rule.severity,
                key=key,
                message=f"{key} reached {worst} (> {threshold})",
                snapshot_index=worst_snap.index,
                raw_timestamp=worst_snap.raw_timestamp,
                observed=worst,
                expected=f"<= {threshold}",
            )
        )
    return findings


@check("delta_limit")
def check_delta_limit(rule: RuleSpec, log: LogFile) -> list[Finding]:
    """Flag if the change between consecutive samples exceeds ``max_delta``."""
    key = _require_key(rule)
    max_delta = rule.params["max_delta"]
    findings: list[Finding] = []
    prev = None
    for snap in log.snapshots:
        val = snap.as_float(key)
        if val is None:
            continue
        if prev is not None and abs(val - prev) > max_delta:
            findings.append(
                Finding(
                    rule_id=rule.id,
                    severity=rule.severity,
                    key=key,
                    message=f"{key} jumped by {abs(val - prev):g} (> {max_delta})",
                    snapshot_index=snap.index,
                    raw_timestamp=snap.raw_timestamp,
                    observed=val,
                    expected=f"|delta| <= {max_delta}",
                )
            )
        prev = val
    return findings
