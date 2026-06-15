"""Log parsers. Each parser turns a raw file into a :class:`LogFile`."""

from loginspect.parsers import snapshot_text  # noqa: F401  (registers parser)
from loginspect.parsers.base import BaseParser, available_formats, get_parser, register_parser

__all__ = ["BaseParser", "register_parser", "get_parser", "available_formats"]
