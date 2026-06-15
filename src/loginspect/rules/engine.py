"""The engine ties a spec to checks and runs them against a log."""

from __future__ import annotations

from dataclasses import dataclass, field

from loginspect.model import Finding, LogFile, Severity
from loginspect.rules.checks import CHECK_TYPES
from loginspect.rules.spec import SpecBundle


@dataclass(slots=True)
class ReviewResult:
    log_path: str
    spec_name: str
    spec_version: str
    snapshot_count: int
    findings: list[Finding] = field(default_factory=list)
    rule_errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no finding is ERROR or worse."""
        return all(f.severity < Severity.ERROR for f in self.findings)

    def counts_by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {s.name: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.name] += 1
        return out


class RuleEngine:
    def __init__(self, spec: SpecBundle):
        self.spec = spec

    def review(self, log: LogFile) -> ReviewResult:
        result = ReviewResult(
            log_path=log.path,
            spec_name=self.spec.name,
            spec_version=self.spec.version,
            snapshot_count=len(log),
        )
        for rule in self.spec.rules:
            if not rule.enabled:
                continue
            fn = CHECK_TYPES.get(rule.check)
            if fn is None:
                result.rule_errors.append(
                    f"Rule {rule.id!r}: unknown check type {rule.check!r}"
                )
                continue
            try:
                result.findings.extend(fn(rule, log))
            except Exception as exc:  # noqa: BLE001 - surface, don't crash
                result.rule_errors.append(f"Rule {rule.id!r} failed: {exc}")
        result.findings.sort(
            key=lambda f: (-f.severity, f.snapshot_index or 0, f.rule_id)
        )
        return result
