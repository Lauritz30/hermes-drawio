"""Built-in layered auto-layout (no CLI needed) — port of pi-drawio's layout.ts.

Assigns a topological layer (longest path from sources) to every node, then positions them either
top-to-bottom or left-to-right. Swimlane-aware: when lanes exist, nodes are laid out left-to-right
inside their lane, and lanes stack vertically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .model import Cell, CellGeometry, Page
from .styles import is_swimlane

MARGIN = 40
COL_GAP = 40
ROW_GAP = 40
PAD = 20
HEADER = 30
LANE_GAP = 20


@dataclass
class NodeInfo:
    cell: Cell
    w: float
    h: float
    lane_id: Optional[str]


def apply_layered_layout(page: Page, direction: str = "vertical") -> None:
    cells = page.cells
    lane_cells = [c for c in cells if c.vertex and is_swimlane(c.style)]
    lane_ids: Set[str] = {c.id for c in lane_cells}

    nodes: List[NodeInfo] = []
    for c in cells:
        if not c.vertex or c.edge:
            continue
        if c.id in ("0", "1"):
            continue
        if is_swimlane(c.style):
            continue
        g = c.geometry
        w = g.width if (g and g.width and g.width > 0) else 120.0
        h = g.height if (g and g.height and g.height > 0) else 60.0
        lane_id = c.parent if (c.parent and c.parent in lane_ids) else None
        # Ungrouped node in a swimlane diagram → first lane.
        if lane_cells and lane_id is None:
            lane_id = lane_cells[0].id
        nodes.append(NodeInfo(cell=c, w=w, h=h, lane_id=lane_id))

    edges = [c for c in cells if c.edge and c.source and c.target]
    layers = compute_layers(
        [n.cell.id for n in nodes],
        [(e.source, e.target) for e in edges],
    )

    max_w = max([60.0] + [n.w for n in nodes])
    max_h = max([40.0] + [n.h for n in nodes])
    max_layer = max([0] + list(layers.values()))

    if lane_cells:
        rows = []
        for lc in lane_cells:
            in_lane = [n for n in nodes if n.lane_id == lc.id]
            content_h = max([60.0] + [n.h for n in in_lane])
            rows.append((lc, in_lane, content_h))

        content_w = (max_layer + 1) * max_w + max_layer * COL_GAP
        lane_w = content_w + 2 * PAD
        y = float(MARGIN)

        for lc, in_lane, content_h in rows:
            lane_h = HEADER + content_h + 2 * PAD
            lc.geometry = CellGeometry(x=MARGIN, y=y, width=lane_w, height=lane_h)
            for n in in_lane:
                layer = layers.get(n.cell.id, 0)
                x_rel = PAD + layer * (max_w + COL_GAP) + (max_w - n.w) / 2
                y_rel = HEADER + PAD + (content_h - n.h) / 2
                n.cell.parent = lc.id
                n.cell.geometry = CellGeometry(x=x_rel, y=y_rel, width=n.w, height=n.h)
            y += lane_h + LANE_GAP
    else:
        groups: Dict[int, List[NodeInfo]] = {}
        for n in nodes:
            layer = layers.get(n.cell.id, 0)
            groups.setdefault(layer, []).append(n)
        max_count = max([1] + [len(g) for g in groups.values()])
        total_w = max_count * max_w + (max_count - 1) * COL_GAP
        total_h = (max_layer + 1) * max_h + max_layer * ROW_GAP

        for layer, group in groups.items():
            for idx, n in enumerate(group):
                if direction == "horizontal":
                    x = MARGIN + layer * (max_w + COL_GAP)
                    group_h = len(group) * max_h + (len(group) - 1) * ROW_GAP
                    y = MARGIN + (total_h - group_h) / 2 + idx * (max_h + ROW_GAP)
                    n.cell.geometry = CellGeometry(x=x, y=y, width=n.w, height=n.h)
                else:
                    y = MARGIN + layer * (max_h + ROW_GAP)
                    group_w = len(group) * max_w + (len(group) - 1) * COL_GAP
                    x = MARGIN + (total_w - group_w) / 2 + idx * (max_w + COL_GAP)
                    n.cell.geometry = CellGeometry(x=x, y=y, width=n.w, height=n.h)

    for e in edges:
        e.geometry = CellGeometry(relative=True)


def compute_layers(node_ids: List[str], edges: List[tuple]) -> Dict[str, int]:
    """Longest-path layer assignment (Kahn's algorithm); cycles get appended layers."""
    succ: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    pred: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    ids: Set[str] = set(node_ids)
    for source, target in edges:
        if source in ids and target in ids and source != target:
            succ[source].append(target)
            pred[target].append(source)

    indeg: Dict[str, int] = {nid: len(pred[nid]) for nid in node_ids}
    layer: Dict[str, int] = {nid: 0 for nid in node_ids}

    queue: List[str] = [nid for nid in node_ids if indeg[nid] == 0]
    visited: Set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for successor in succ[current]:
            layer[successor] = max(layer[successor], layer[current] + 1)
            indeg[successor] -= 1
            if indeg[successor] == 0:
                queue.append(successor)

    # Cycle leftovers get appended layers so they don't overlap.
    max_layer = max(layer.values()) if layer else 0
    for nid in node_ids:
        if nid not in visited:
            max_layer += 1
            layer[nid] = max_layer
    return layer
