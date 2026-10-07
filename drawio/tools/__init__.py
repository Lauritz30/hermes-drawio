"""Tool handlers — what runs when the model calls a draw.io tool.

Import surface for the handlers; ``HANDLERS`` maps every tool name to its callable.
"""

from __future__ import annotations

from .handlers import HANDLERS

__all__ = ["HANDLERS"]
