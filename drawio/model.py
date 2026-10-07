"""Core intermediate representation (IR) for draw.io diagrams.

The plugin reads and writes native ``.drawio`` (mxGraphModel) XML and works through this
plain-Python model in between. Fields mirror the pi-drawio TypeScript IR so the behavior
(layout, coloring, round-tripping) stays 1:1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Point:
    """A single x/y coordinate (edge waypoints)."""

    x: float
    y: float


@dataclass
class CellGeometry:
    """``<mxGeometry>`` content of a cell."""

    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    relative: bool = False
    points: List[Point] = field(default_factory=list)


@dataclass
class Cell:
    """A single mxCell: root, layer, swimlane, node, or edge."""

    id: str
    value: Optional[str] = None
    style: Optional[str] = None
    vertex: bool = False
    edge: bool = False
    parent: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    geometry: Optional[CellGeometry] = None
    # Unknown attributes preserved across round-trips (e.g. hand-authored files).
    extra_attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class Page:
    """One ``<diagram>`` (a page) inside an mxfile."""

    id: str
    name: str
    cells: List[Cell] = field(default_factory=list)


@dataclass
class Diagram:
    """A parsed ``.drawio`` file: one or more pages."""

    pages: List[Page] = field(default_factory=list)


@dataclass(frozen=True)
class RoleColor:
    """A fill/stroke/header color triple for a role or lane."""

    name: str
    fill: str
    stroke: str
    header: str


@dataclass(frozen=True)
class ShapeDef:
    """A named shape's mxGraph style string and default size."""

    style: str
    width: float
    height: float
