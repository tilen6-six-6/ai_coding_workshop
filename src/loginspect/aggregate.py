"""Collapse runs of identical findings into single grouped findings.

A persistent condition (e.g. ``service_status == ERROR`` across 2900 snapshots)
otherwise produces one finding per snapshot, which is noise. Collapsing groups
findings that share ``(rule_id, key, message-shape)`` into a single record with
an occurrence count and the first/last snapshot it was seen in.
"""

from __future__ import annotations

from dataclasses import dataclass

from loginspect.model import Finding, Severity


@dataclass(slots=True)
class GroupedFinding:
    rule_id: str
    severity: Severity
    key: str
    message: str
    count: int
    first_index: int | None
    last_index: int | None
    first_timestamp: str | None
    last_timestamp: str | None
    sample_observed: object = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.name,
            "key": self.key,
            "message": self.message,
            "count": self.count,
            "first_index": self.first_index,
            "last_index": self.last_index,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "sample_observed": self.sample_observed,
        }


def collapse(findings: list[Finding]) -> list[GroupedFinding]:
    """Group findings by (rule_id, key). Findings within a group are summarized
    with a count and the span of snapshots they cover."""
    groups: dict[tuple[str, str], GroupedFinding] = {}
    order: list[tuple[str, str]] = []
    for f in findings:
        gkey = (f.rule_id, f.key)
        if gkey not in groups:
            groups[gkey] = GroupedFinding(
                rule_id=f.rule_id,
                severity=f.severity,
                key=f.key,
                message=f.message,
                count=1,
                first_index=f.snapshot_index,
                last_index=f.snapshot_index,
                first_timestamp=f.raw_timestamp,
                last_timestamp=f.raw_timestamp,
                sample_observed=f.observed,
            )
            order.append(gkey)
        else:
            g = groups[gkey]
            g.count += 1
            if f.snapshot_index is not None:
                if g.last_index is None or f.snapshot_index > g.last_index:
                    g.last_index = f.snapshot_index
                    g.last_timestamp = f.raw_timestamp
                if g.first_index is None or f.snapshot_index < g.first_index:
                    g.first_index = f.snapshot_index
                    g.first_timestamp = f.raw_timestamp
    result = [groups[k] for k in order]
    result.sort(key=lambda g: (-g.severity, g.first_index or 0, g.rule_id))
    return result
