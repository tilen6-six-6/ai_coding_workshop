"""Report renderers: turn a ReviewResult into text, JSON, or HTML."""

from loginspect.report.renderers import (
    render_html,
    render_json,
    render_text,
    render_text_collapsed,
)

__all__ = ["render_text", "render_text_collapsed", "render_json", "render_html"]
