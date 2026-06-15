"""Shared data types for the log compliance checker."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class LogEntry:
    """A single normalized log entry.

    `raw` is the original line/text. `fields` holds parsed key/value data
    (e.g. {"level": "ERROR", "code": 500}). `line_no` is 1-based position
    in the source file. `timestamp` is an ISO string if one was found.
    """
    line_no: int
    raw: str
    fields: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)


@dataclass
class Issue:
    """A single compliance violation."""
    rule_id: str
    severity: str           # "info" | "warning" | "error" | "critical"
    message: str
    line_no: Optional[int] = None
    log_excerpt: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    """Result of running all rules over all log entries."""
    issues: List[Issue] = field(default_factory=list)
    entries_checked: int = 0
    rules_evaluated: int = 0

    @property
    def passed(self) -> bool:
        return not any(i.severity in ("error", "critical") for i in self.issues)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "entries_checked": self.entries_checked,
            "rules_evaluated": self.rules_evaluated,
            "issue_count": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
        }
