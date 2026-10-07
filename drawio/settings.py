"""A single mutable place for plugin configuration resolved at registration time.

The plugin reads its optional ``drawio_path`` setting from Hermes's plugin config namespace, which
belongs at registration time but is needed by helpers deeper in the stack; keeping it here avoids
threading the value through every call site (mirrors the hermes-jira-multiproject pattern).
"""

from __future__ import annotations

from typing import Optional

_DRAWIO_PATH: dict = {"value": None}


def set_drawio_path(value: Optional[str]) -> None:
    """Record the configured draw.io CLI override (``None``/empty clears it)."""
    cleaned = str(value).strip() if value else ""
    _DRAWIO_PATH["value"] = cleaned or None


def drawio_path_override() -> Optional[str]:
    """Configured draw.io CLI override, or ``None`` to use env/default detection."""
    return _DRAWIO_PATH["value"]


__all__ = ["drawio_path_override", "set_drawio_path"]
