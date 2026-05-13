"""Source registry — maps domains to source modules."""

from __future__ import annotations

import logging
from typing import Any, Protocol
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Source Protocol ──────────────────────────────────────────────────────


class StreamSource(Protocol):
    """Interface each source must implement."""

    name: str
    domains: list[str]

    @staticmethod
    def search(query: str) -> list[dict[str, Any]]: ...

    @staticmethod
    def get_stream_url(url: str, **kwargs: Any) -> str | None: ...

    @staticmethod
    def get_content_info(url: str) -> dict[str, Any]: ...


# ── Registry ─────────────────────────────────────────────────────────────


_registry: dict[str, type[StreamSource]] = {}


def register(source_cls: type[StreamSource]) -> type[StreamSource]:
    """Register a source module."""
    for domain in source_cls.domains:
        _registry[domain] = source_cls
    logger.debug("Registered source: %s (%s)", source_cls.name, ", ".join(source_cls.domains))
    return source_cls


def detect_source(url: str) -> type[StreamSource] | None:
    """Detect which source handles a given URL."""
    host = urlparse(url).hostname or ""
    for domain, source_cls in _registry.items():
        if domain in host:
            return source_cls
    return None


def list_sources() -> list[type[StreamSource]]:
    """Return all registered source classes."""
    return list(set(_registry.values()))


def search_all(query: str) -> list[dict[str, Any]]:
    """Search all sources and return merged results with source label."""
    results: list[dict[str, Any]] = []
    for source_cls in list_sources():
        if hasattr(source_cls, "search"):
            try:
                items = source_cls.search(query)
                for item in items:
                    item.setdefault("source", source_cls.name)
                results.extend(items)
            except Exception as e:
                logger.warning("Search failed for %s: %s", source_cls.name, e)
    return results
