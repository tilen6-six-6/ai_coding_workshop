"""Parser registry so new log formats can be added without touching callers."""

from __future__ import annotations

import abc

from loginspect.model import LogFile

_REGISTRY: dict[str, BaseParser] = {}


class BaseParser(abc.ABC):
    """A parser converts a raw log file on disk into a :class:`LogFile`."""

    #: Short identifier used on the command line, e.g. ``snapshot-text``.
    name: str = "base"

    @abc.abstractmethod
    def sniff(self, sample: str) -> bool:
        """Return True if this parser can likely handle ``sample`` text."""

    @abc.abstractmethod
    def parse(self, path: str) -> LogFile:
        """Parse the file at ``path`` into a :class:`LogFile`."""


def register_parser(parser):
    """Register a parser. Accepts either a class or an instance."""
    instance = parser() if isinstance(parser, type) else parser
    _REGISTRY[instance.name] = instance
    return parser


def get_parser(name: str) -> BaseParser:
    if name not in _REGISTRY:
        raise KeyError(f"No parser named {name!r}. Available: {available_formats()}")
    return _REGISTRY[name]


def available_formats() -> list[str]:
    return sorted(_REGISTRY)


def autodetect(path: str, sample_bytes: int = 4096) -> BaseParser:
    """Pick a parser by sniffing the start of the file."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        sample = fh.read(sample_bytes)
    for parser in _REGISTRY.values():
        if parser.sniff(sample):
            return parser
    raise ValueError(
        f"Could not autodetect a parser for {path!r}. "
        f"Specify one explicitly: {available_formats()}"
    )
