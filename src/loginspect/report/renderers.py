"""Render review results in several formats."""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

from loginspect.model import Severity

if TYPE_CHECKING:
    from loginspect.rules.engine import ReviewResult


def render_json(result: ReviewResult) -> str:
    payload = {
        "log_path": result.log_path,
        "spec": {"name": result.spec_name, "version": result.spec_version},
        "snapshot_count": result.snapshot_count,
        "passed": result.passed,
        "summary": result.counts_by_severity(),
        "rule_errors": result.rule_errors,
        "findings": [f.to_dict() for f in result.findings],
    }
    return json.dumps(payload, indent=2)


def render_text(result: ReviewResult, max_findings: int = 200) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("LogInspect review")
    lines.append("=" * 70)
    lines.append(f"Log:       {result.log_path}")
    lines.append(f"Spec:      {result.spec_name} v{result.spec_version}")
    lines.append(f"Snapshots: {result.snapshot_count}")
    status = "PASS" if result.passed else "FAIL"
    lines.append(f"Result:    {status}")
    lines.append("")
    counts = result.counts_by_severity()
    lines.append("Summary by severity:")
    for sev in sorted(Severity, reverse=True):
        lines.append(f"  {sev.name:<9} {counts[sev.name]}")
    lines.append("")

    if result.rule_errors:
        lines.append("Rule errors (spec problems, not log problems):")
        for err in result.rule_errors:
            lines.append(f"  ! {err}")
        lines.append("")

    if not result.findings:
        lines.append("No findings. Everything within spec.")
        return "\n".join(lines)

    lines.append(f"Findings ({len(result.findings)} total):")
    for f in result.findings[:max_findings]:
        loc = f"snap#{f.snapshot_index}" if f.snapshot_index is not None else "global"
        ts = f" @ {f.raw_timestamp}" if f.raw_timestamp else ""
        lines.append(f"  [{f.severity.name:<8}] {f.rule_id} ({loc}{ts})")
        lines.append(f"             {f.message}")
    if len(result.findings) > max_findings:
        lines.append(f"  ... and {len(result.findings) - max_findings} more")
    return "\n".join(lines)


def render_text_collapsed(result: ReviewResult) -> str:
    from loginspect.aggregate import collapse

    groups = collapse(result.findings)
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("LogInspect review (collapsed)")
    lines.append("=" * 70)
    lines.append(f"Log:       {result.log_path}")
    lines.append(f"Spec:      {result.spec_name} v{result.spec_version}")
    lines.append(f"Snapshots: {result.snapshot_count}")
    lines.append(f"Result:    {'PASS' if result.passed else 'FAIL'}")
    lines.append("")
    counts = result.counts_by_severity()
    lines.append("Summary by severity (raw findings):")
    for sev in sorted(Severity, reverse=True):
        lines.append(f"  {sev.name:<9} {counts[sev.name]}")
    lines.append("")
    if result.rule_errors:
        lines.append("Rule errors:")
        for err in result.rule_errors:
            lines.append(f"  ! {err}")
        lines.append("")
    if not groups:
        lines.append("No findings. Everything within spec.")
        return "\n".join(lines)
    lines.append(f"Distinct issues ({len(groups)}):")
    for g in groups:
        span = (
            f"snap {g.first_index}–{g.last_index}"
            if g.first_index != g.last_index
            else f"snap {g.first_index}"
        )
        lines.append(
            f"  [{g.severity.name:<8}] {g.rule_id} ×{g.count}  ({span})"
        )
        lines.append(f"             {g.message}")
    return "\n".join(lines)


def render_html(result: ReviewResult) -> str:
    from loginspect.aggregate import collapse

    groups = collapse(result.findings)
    counts = result.counts_by_severity()
    status = "PASS" if result.passed else "FAIL"
    status_color = "#1a7f37" if result.passed else "#cf222e"

    sev_color = {
        "CRITICAL": "#cf222e",
        "ERROR": "#d1242f",
        "WARNING": "#9a6700",
        "INFO": "#0969da",
    }

    rows = []
    for g in groups:
        if g.first_index == g.last_index:
            span = f"#{g.first_index}" if g.first_index is not None else "—"
        else:
            span = f"#{g.first_index}–{g.last_index}"
        ts = html.escape(
            f"{g.first_timestamp} → {g.last_timestamp}"
            if g.first_timestamp and g.first_timestamp != g.last_timestamp
            else (g.first_timestamp or "")
        )
        rows.append(
            f"<tr class='sev-{g.severity.name.lower()}'>"
            f"<td><span class='badge' style='background:{sev_color[g.severity.name]}'>"
            f"{g.severity.name}</span></td>"
            f"<td>{html.escape(g.rule_id)}</td>"
            f"<td class='mono'>{html.escape(g.key)}</td>"
            f"<td>{html.escape(g.message)}</td>"
            f"<td class='mono'>{g.count}</td>"
            f"<td class='mono'>{span}</td>"
            f"<td class='mono'>{ts}</td></tr>"
        )
    rows_html = "\n".join(rows) or (
        "<tr><td colspan='7'>No findings — everything within spec.</td></tr>"
    )

    chips = "".join(
        f"<span class='chip' style='border-color:{sev_color[s]}'>"
        f"<b style='color:{sev_color[s]}'>{counts[s]}</b> {s}</span>"
        for s in ("CRITICAL", "ERROR", "WARNING", "INFO")
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LogInspect Report</title>
<style>
  :root {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  body {{ margin: 0; background: #f6f8fa; color: #1f2328; }}
  header {{ background: #fff; border-bottom: 1px solid #d0d7de; padding: 24px 32px; }}
  h1 {{ margin: 0 0 4px; font-size: 20px; }}
  .meta {{ color: #656d76; font-size: 13px; }}
  .status {{ display:inline-block; font-weight:700; color:#fff; background:{status_color};
            padding:4px 12px; border-radius:6px; margin-left:8px; }}
  main {{ padding: 24px 32px; }}
  .chips {{ margin: 0 0 20px; display:flex; gap:8px; flex-wrap:wrap; }}
  .chip {{ background:#fff; border:1px solid; border-radius:20px; padding:4px 12px; font-size:13px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #d0d7de;
           border-radius:8px; overflow:hidden; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 12px; border-bottom:1px solid #eaeef2; vertical-align:top; }}
  th {{ background:#f6f8fa; font-weight:600; }}
  tr:last-child td {{ border-bottom:none; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .badge {{ color:#fff; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600; }}
  tr.sev-critical, tr.sev-error {{ background:#fff8f8; }}
</style></head>
<body>
<header>
  <h1>LogInspect Report <span class="status">{status}</span></h1>
  <div class="meta">
    Log: <span class="mono">{html.escape(result.log_path)}</span><br>
    Spec: {html.escape(result.spec_name)} v{html.escape(result.spec_version)} ·
    {result.snapshot_count} snapshots · {len(result.findings)} findings · {len(groups)} distinct issues
  </div>
</header>
<main>
  <div class="chips">{chips}</div>
  <table>
    <thead><tr><th>Severity</th><th>Rule</th><th>Key</th><th>Message</th>
    <th>Count</th><th>Snapshots</th><th>Time span</th></tr></thead>
    <tbody>
    {rows_html}
    </tbody>
  </table>
</main>
</body></html>"""
