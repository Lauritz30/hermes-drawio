"""Role/lane color assignment (port of pi-drawio's colors.ts).

One role = one color, deterministically, so the same role keeps the same color across diagrams.
A role name maps to a palette slot via a stable string hash; within a single diagram collisions
are resolved so distinct roles always get distinct colors.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .model import RoleColor

# Light, accessible fills (100-series) with mid-tone strokes (500-series).
PALETTE: List[RoleColor] = [
    RoleColor(name="blue", fill="#DBEAFE", stroke="#3B82F6", header="#BFDBFE"),
    RoleColor(name="green", fill="#D1FAE5", stroke="#10B981", header="#A7F3D0"),
    RoleColor(name="red", fill="#FEE2E2", stroke="#EF4444", header="#FECACA"),
    RoleColor(name="amber", fill="#FEF3C7", stroke="#F59E0B", header="#FDE68A"),
    RoleColor(name="purple", fill="#EDE9FE", stroke="#8B5CF6", header="#DDD6FE"),
    RoleColor(name="pink", fill="#FCE7F3", stroke="#EC4899", header="#FBCFE8"),
    RoleColor(name="cyan", fill="#CFFAFE", stroke="#06B6D4", header="#A5F3FC"),
    RoleColor(name="teal", fill="#CCFBF1", stroke="#14B8A6", header="#99F6E4"),
    RoleColor(name="indigo", fill="#E0E7FF", stroke="#6366F1", header="#C7D2FE"),
    RoleColor(name="orange", fill="#FFEDD5", stroke="#F97316", header="#FED7AA"),
    RoleColor(name="lime", fill="#ECFCCB", stroke="#84CC16", header="#D9F99D"),
    RoleColor(name="slate", fill="#F1F5F9", stroke="#64748B", header="#E2E8F0"),
]

# draw.io's classic default shape fill, used for un-colored nodes.
DEFAULT_COLOR = RoleColor(name="default-blue", fill="#DAE8FC", stroke="#6C8EBF", header="#DAE8FC")

_FILL_RE = re.compile(r"(?:^|;)fillColor=([^;]+)")
_STROKE_RE = re.compile(r"(?:^|;)strokeColor=([^;]+)")
_HEADER_RE = re.compile(r"(?:^|;)swimlaneFillColor=([^;]+)")


def _hash_string(s: str) -> int:
    """Stable 32-bit string hash matching pi-drawio's JavaScript hashString()."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def color_by_index(i: int) -> RoleColor:
    return PALETTE[i % len(PALETTE)]


def color_index_for(role: str) -> int:
    """Stable palette index for a role name (0..len(PALETTE)-1)."""
    r = (role or "").strip()
    for idx, color in enumerate(PALETTE):
        if color.name.lower() == r.lower():
            return idx
    return _hash_string(r) % len(PALETTE)


def role_color(role: Optional[str] = None) -> RoleColor:
    """Deterministic color for a single role (collisions possible with many roles)."""
    if not role:
        return DEFAULT_COLOR
    return PALETTE[color_index_for(role)]


def assign_role_colors(roles: List[str]) -> Dict[str, RoleColor]:
    """Assign a distinct palette color to each role key, in first-seen order.

    Colors stay stable across diagrams (hash-based), but collisions within the same diagram are
    resolved so two roles never share a color there.
    """
    mapping: Dict[str, RoleColor] = {}
    used: set = set()
    for role in roles:
        if role in mapping:
            continue
        idx = color_index_for(role)
        while idx in used:
            idx = (idx + 1) % len(PALETTE)
        used.add(idx)
        mapping[role] = PALETTE[idx]
    return mapping


def parse_color(style: Optional[str]) -> Optional[RoleColor]:
    """Read the fill/stroke colors back out of a style string, if present."""
    if not style:
        return None
    fill = _FILL_RE.search(style)
    stroke = _STROKE_RE.search(style)
    header = _HEADER_RE.search(style)
    fill_v = fill.group(1) if fill else None
    stroke_v = stroke.group(1) if stroke else None
    header_v = header.group(1) if header else None
    if not fill_v and not stroke_v:
        return None
    return RoleColor(
        name="custom",
        fill=fill_v or "#FFFFFF",
        stroke=stroke_v or "#333333",
        header=header_v or fill_v or "#FFFFFF",
    )
