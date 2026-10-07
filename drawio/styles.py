"""Named shape/edge styles → mxGraph style strings, plus color merging (port of styles.ts)."""

from __future__ import annotations

import re
from typing import Dict, Optional

from .model import RoleColor, ShapeDef

SHAPES: Dict[str, ShapeDef] = {
    "rounded": ShapeDef(style="rounded=1;whiteSpace=wrap;html=1;", width=120, height=60),
    "rectangle": ShapeDef(style="whiteSpace=wrap;html=1;", width=120, height=60),
    "ellipse": ShapeDef(style="ellipse;whiteSpace=wrap;html=1;", width=120, height=60),
    "terminator": ShapeDef(style="ellipse;whiteSpace=wrap;html=1;", width=140, height=50),
    "diamond": ShapeDef(style="rhombus;whiteSpace=wrap;html=1;", width=140, height=90),
    "parallelogram": ShapeDef(
        style="shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;",
        width=130,
        height=60,
    ),
    "hexagon": ShapeDef(
        style="shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;",
        width=130,
        height=70,
    ),
    "document": ShapeDef(style="shape=document;whiteSpace=wrap;html=1;boundedLbl=1;", width=120, height=80),
    "database": ShapeDef(
        style="shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;",
        width=90,
        height=80,
    ),
    "cloud": ShapeDef(style="ellipse;shape=cloud;whiteSpace=wrap;html=1;", width=140, height=80),
    "text": ShapeDef(
        style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;",
        width=120,
        height=30,
    ),
    "swimlane": ShapeDef(
        style="swimlane;html=1;horizontal=1;startSize=30;fontStyle=1;whiteSpace=wrap;",
        width=220,
        height=200,
    ),
}

DEFAULT_SHAPE = "rounded"

# Matches fillColor=..., strokeColor=..., swimlaneFillColor=... (with optional leading ;).
_COLOR_KEYS_RE = re.compile(r"(fillColor|strokeColor|swimlaneFillColor)=[^;]*;?")


def resolve_shape(name: Optional[str] = None) -> ShapeDef:
    return SHAPES.get(name or "") or SHAPES[DEFAULT_SHAPE]


def is_swimlane(style: Optional[str]) -> bool:
    """True when the style marks a swimlane container."""
    return bool(style) and bool(re.search(r"\bswimlane\b", style or ""))


def with_color(style: str, color: RoleColor, header: bool = False) -> str:
    """Append/override fillColor & strokeColor on a style string.

    ``header`` also sets the swimlane header fill (swimlaneFillColor).
    """
    s = _COLOR_KEYS_RE.sub("", style).rstrip(";")
    out = f"{s};fillColor={color.fill};strokeColor={color.stroke};"
    if header:
        out += f"swimlaneFillColor={color.header};"
    return out


def swimlane_style(color: RoleColor) -> str:
    return with_color(SHAPES["swimlane"].style, color, header=True)


def edge_style(kind: str, color: Optional[RoleColor] = None) -> str:
    """``kind`` is one of "arrow", "line", "dashed"."""
    s = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
    if kind == "line":
        s += "endArrow=none;"
    elif kind == "dashed":
        s += "dashed=1;endArrow=none;"
    else:
        s += "endArrow=block;endFill=1;"
    if color:
        s += f"strokeColor={color.stroke};"
    return s
