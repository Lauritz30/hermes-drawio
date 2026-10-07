"""High-level draw.io operations shared by the tools (port of pi-drawio's engine.ts).

create / add / update / delete / list / read-write raw XML / export / open / layout. Everything
works on native ``.drawio`` (mxGraphModel) XML through the IR in :mod:`drawio.model`; nothing here
touches an MCP server — all local.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from . import paths
from .cli import (
    apply_layout,
    drawio_available,
    export_diagram,
    find_drawio,
    open_diagram_in_editor,
    open_path,
)
from .colors import (
    DEFAULT_COLOR,
    assign_role_colors,
    color_by_index,
    parse_color,
    role_color,
)
from .layout import apply_layered_layout
from .model import Cell, CellGeometry, Diagram, Page, RoleColor
from .parse import parse_diagram, validate_xml
from .serialize import serialize_diagram
from .styles import edge_style, is_swimlane, resolve_shape, swimlane_style, with_color


def _abs(path: str, task_id: str) -> str:
    """Resolve a (possibly relative) path to an absolute, task-anchored path."""
    return paths.resolve_file(path, task_id)


def _gen_id(used: Set[str], prefix: str) -> str:
    i = 1
    while f"{prefix}{i}" in used:
        i += 1
    return f"{prefix}{i}"


def empty_page() -> Page:
    """A fresh single-page diagram with the standard root (0) and layer (1) cells."""
    return Page(id="page-1", name="Page-1", cells=[Cell(id="0"), Cell(id="1", parent="0")])


def _load_diagram(abs_path: str) -> Diagram:
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"Diagram not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as handle:
        return parse_diagram(handle.read())


def _save_diagram(abs_path: str, diagram: Diagram) -> None:
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as handle:
        handle.write(serialize_diagram(diagram))


def _color_from_hex(hex_val: Optional[str], fallback: Optional[str] = None) -> Optional[RoleColor]:
    if not hex_val:
        return None
    stroke = fallback or hex_val
    return RoleColor(name="custom", fill=hex_val, stroke=stroke, header=hex_val)


@dataclass
class BuildResult:
    lanes: List[Cell] = field(default_factory=list)
    nodes: List[Cell] = field(default_factory=list)
    edges: List[Cell] = field(default_factory=list)


def build_cells(spec: Dict[str, Any], page: Page) -> BuildResult:
    """Materialize lane/node/edge cells from a spec into *page*.

    Resolves lane references (by id or name), assigns colors (stable per role, distinct per
    diagram), and generates collision-free stable ids. Mirrors pi-drawio's ``buildCells``.
    """
    lanes = spec.get("lanes") or []
    nodes = spec.get("nodes") or []
    edges = spec.get("edges") or []

    used: Set[str] = {c.id for c in page.cells}
    result = BuildResult()

    # Index existing lanes by id and by header name.
    lane_by_key: Dict[str, Cell] = {}
    lane_color: Dict[str, RoleColor] = {}
    for c in page.cells:
        if c.vertex and is_swimlane(c.style):
            lane_by_key[c.id] = c
            if c.value:
                lane_by_key[c.value] = c
            lane_color[c.id] = parse_color(c.style) or DEFAULT_COLOR

    # Stable, collision-free colors for every role-like key in this call.
    role_keys: List[str] = []
    for l in lanes:
        if l.get("role"):
            role_keys.append(l["role"])
        elif l.get("name"):
            role_keys.append(l["name"])
        for n in l.get("nodes") or []:
            if n.get("role"):
                role_keys.append(n["role"])
    for n in nodes:
        if n.get("role"):
            role_keys.append(n["role"])
    role_color_map = assign_role_colors(role_keys)
    lane_counter = len(lane_color)

    # 1) Lanes.
    for ls in lanes:
        existing = (ls.get("id") and lane_by_key.get(ls["id"])) or (
            ls.get("name") and lane_by_key.get(ls["name"])
        )
        if existing:
            continue

        id_ = ls.get("id") if ls.get("id") and ls["id"] not in used else _gen_id(used, "lane")
        role_key = ls.get("role") or ls.get("name") or ""
        color = _color_from_hex(ls.get("color"))
        if color is None:
            color = role_color_map.get(role_key)
        if color is None:
            if role_key:
                color = role_color(role_key)
            else:
                color = color_by_index(lane_counter)
                lane_counter += 1
        label = ls.get("name") or ls.get("role") or ls.get("id") or id_

        cell = Cell(id=id_, value=label, vertex=True, parent="1", style=swimlane_style(color))
        used.add(id_)
        result.lanes.append(cell)
        page.cells.append(cell)
        lane_by_key[id_] = cell
        if ls.get("name"):
            lane_by_key[ls["name"]] = cell
        lane_color[id_] = color

    # 2) Nodes (top-level + nested in lanes).
    node_specs: List[Dict[str, Any]] = []
    for ls in lanes:
        for n in ls.get("nodes") or []:
            merged = dict(n)
            merged["lane"] = n.get("lane") or ls.get("id") or ls.get("name")
            node_specs.append(merged)
    for n in nodes:
        node_specs.append(dict(n))

    for ns in node_specs:
        lane_id: Optional[str] = None
        if ns.get("lane"):
            existing = lane_by_key.get(ns["lane"])
            if existing:
                lane_id = existing.id
            else:
                # Auto-create a lane for an unknown lane name.
                id_ = _gen_id(used, "lane")
                role_key = ns.get("role") or ns.get("lane") or ""
                color = (
                    _color_from_hex(ns.get("fillColor"))
                    or role_color_map.get(role_key)
                    or role_color(role_key)
                )
                cell = Cell(id=id_, value=ns["lane"], vertex=True, parent="1",
                            style=swimlane_style(color))
                used.add(id_)
                result.lanes.append(cell)
                page.cells.append(cell)
                lane_by_key[ns["lane"]] = cell
                lane_by_key[id_] = cell
                lane_color[id_] = color
                lane_id = id_

        shape_name = ns.get("shape") or "rounded"
        shape = resolve_shape(shape_name)
        w = ns.get("width") if ns.get("width") is not None else shape.width
        h = ns.get("height") if ns.get("height") is not None else shape.height

        if shape_name == "text":
            color: RoleColor = RoleColor(name="none", fill="none", stroke="none", header="none")
        else:
            color = _color_from_hex(ns.get("fillColor"), ns.get("strokeColor"))
            if color is None:
                if lane_id:
                    color = lane_color.get(lane_id) or DEFAULT_COLOR
                elif ns.get("role"):
                    color = role_color_map.get(ns["role"]) or role_color(ns["role"])
                else:
                    color = DEFAULT_COLOR

        base_style = ns.get("style") or shape.style
        style = base_style if shape_name == "text" else with_color(base_style, color)

        id_ = ns.get("id") if ns.get("id") and ns["id"] not in used else _gen_id(used, "n")
        used.add(id_)

        cell = Cell(
            id=id_,
            value=ns.get("label") or "",
            vertex=True,
            parent=lane_id or "1",
            style=style,
            geometry=CellGeometry(
                x=ns.get("x") if ns.get("x") is not None else 0.0,
                y=ns.get("y") if ns.get("y") is not None else 0.0,
                width=w,
                height=h,
            ),
        )
        result.nodes.append(cell)
        page.cells.append(cell)

    # 3) Edges.
    for es in edges:
        kind = "dashed" if es.get("dashed") else ("line" if es.get("arrow") is False else "arrow")
        id_ = es.get("id") if es.get("id") and es["id"] not in used else _gen_id(used, "e")
        used.add(id_)
        cell = Cell(
            id=id_,
            value=es.get("label"),
            edge=True,
            parent="1",
            source=es.get("source"),
            target=es.get("target"),
            style=es.get("style") or edge_style(kind),
            geometry=CellGeometry(relative=True),
        )
        result.edges.append(cell)
        page.cells.append(cell)

    return result


def create_diagram(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    page = empty_page()
    if opts.get("title"):
        page.name = opts["title"]

    built = build_cells(
        {"nodes": opts.get("nodes"), "edges": opts.get("edges"), "lanes": opts.get("lanes")},
        page,
    )
    layout = opts.get("layout") or "layered"
    direction = opts.get("direction") or ("horizontal" if built.lanes else "vertical")

    if layout == "layered":
        apply_layered_layout(page, direction)

    _save_diagram(abs_path, Diagram(pages=[page]))

    # CLI-only layout passes (ELK / libavoid) run against the file on disk.
    if layout != "none" and layout != "layered":
        preset = layout[4:] if layout.startswith("elk:") else layout
        if not drawio_available():
            raise RuntimeError(
                f"Layout '{layout}' needs the draw.io desktop CLI (not installed). "
                f'Use layout:"layered" (built-in) or layout:"none". '
                f"The .drawio file was created at {abs_path}."
            )
        apply_layout(abs_path, preset)

    exported: Optional[str] = None
    if opts.get("exportFormat"):
        if not drawio_available():
            raise RuntimeError(
                f"{opts['exportFormat'].upper()} export needs the draw.io desktop app. "
                f"The .drawio file was created at {abs_path}; open it in draw.io or install the "
                "desktop app to export."
            )
        exported = export_diagram(
            abs_path,
            opts["exportFormat"],
            border=opts.get("border") if opts.get("border") is not None else 10,
            scale=opts.get("scale"),
        )

    opened: Optional[str] = None
    if opts.get("open") is not False:
        opened = open_diagram_in_editor(abs_path)
        if exported:
            open_path(exported)

    return {
        "path": abs_path,
        "exported": exported,
        "opened": opened,
        "nodes": len(built.nodes),
        "edges": len(built.edges),
        "lanes": len(built.lanes),
        "drawioCli": drawio_available(),
    }


def add_cells(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"No diagram at {abs_path}. Use drawio_create_diagram first.")
    diagram = _load_diagram(abs_path)
    page = diagram.pages[0] if diagram.pages else empty_page()
    built = build_cells(
        {"nodes": opts.get("nodes"), "edges": opts.get("edges"), "lanes": opts.get("lanes")},
        page,
    )

    layout = opts.get("layout") or "layered"
    if layout == "layered":
        apply_layered_layout(
            page, opts.get("direction") or ("horizontal" if built.lanes else "vertical")
        )
    _save_diagram(abs_path, diagram)

    if layout != "none" and layout != "layered":
        preset = layout[4:] if layout.startswith("elk:") else layout
        if not drawio_available():
            raise RuntimeError(
                f"Layout '{layout}' needs the draw.io desktop CLI (not installed)."
            )
        apply_layout(abs_path, preset)

    opened: Optional[str] = None
    if opts.get("open") is not False:
        opened = open_diagram_in_editor(abs_path)

    return {
        "path": abs_path,
        "nodes": len(built.nodes),
        "edges": len(built.edges),
        "lanes": len(built.lanes),
        "opened": opened,
    }


def update_cells(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    diagram = _load_diagram(abs_path)
    page = diagram.pages[0] if diagram.pages else empty_page()

    updated = 0
    for spec in opts.get("cells") or []:
        cell = next((c for c in page.cells if c.id == spec.get("id")), None)
        if cell is None:
            raise RuntimeError(f"Cell '{spec.get('id')}' not found in {abs_path}")

        if spec.get("label") is not None:
            cell.value = spec["label"]
        if spec.get("style") is not None:
            cell.style = spec["style"]

        if spec.get("shape") and not cell.edge:
            shape = resolve_shape(spec["shape"])
            color = parse_color(cell.style) or DEFAULT_COLOR
            cell.style = shape.style if spec["shape"] == "text" else with_color(shape.style, color)
            if spec.get("width") is None and cell.geometry and not cell.geometry.width:
                cell.geometry.width = shape.width
            if spec.get("height") is None and cell.geometry and not cell.geometry.height:
                cell.geometry.height = shape.height

        if (spec.get("fillColor") or spec.get("strokeColor")) and cell.style:
            cur = parse_color(cell.style) or DEFAULT_COLOR
            cell.style = with_color(
                cell.style,
                RoleColor(
                    name="custom",
                    fill=spec.get("fillColor") or cur.fill,
                    stroke=spec.get("strokeColor") or cur.stroke,
                    header=cur.header,
                ),
            )

        if cell.geometry is None:
            cell.geometry = CellGeometry()
        if spec.get("x") is not None:
            cell.geometry.x = spec["x"]
        if spec.get("y") is not None:
            cell.geometry.y = spec["y"]
        if spec.get("width") is not None:
            cell.geometry.width = spec["width"]
        if spec.get("height") is not None:
            cell.geometry.height = spec["height"]

        updated += 1

    if opts.get("layout") != "none":
        apply_layered_layout(page, "vertical")
    _save_diagram(abs_path, diagram)
    return {"path": abs_path, "updated": updated}


def delete_cells(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    diagram = _load_diagram(abs_path)
    page = diagram.pages[0] if diagram.pages else empty_page()

    to_remove: Set[str] = set(opts.get("ids") or [])
    # Remove edges whose endpoint is removed.
    for c in page.cells:
        if c.edge and ((c.source and c.source in to_remove) or (c.target and c.target in to_remove)):
            to_remove.add(c.id)
    before = len(page.cells)
    page.cells = [c for c in page.cells if c.id not in to_remove]

    if opts.get("layout") != "none":
        apply_layered_layout(page, "vertical")
    _save_diagram(abs_path, diagram)
    return {"path": abs_path, "removed": before - len(page.cells)}


def list_cells(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    diagram = _load_diagram(abs_path)
    page = diagram.pages[0] if diagram.pages else empty_page()

    cells: List[Dict[str, Any]] = []
    for c in page.cells:
        if c.edge:
            kind = "edge"
        elif c.id == "0":
            kind = "root"
        elif c.id == "1":
            kind = "layer"
        elif is_swimlane(c.style):
            kind = "swimlane"
        else:
            kind = "node"
        g = c.geometry
        geom: Optional[Dict[str, Any]] = None
        if g is not None:
            geom = {
                k: v
                for k, v in {"x": g.x, "y": g.y, "width": g.width, "height": g.height}.items()
                if v is not None
            }
        cells.append(
            {
                "id": c.id,
                "kind": kind,
                "label": c.value,
                "parent": c.parent,
                "source": c.source,
                "target": c.target,
                "geometry": geom,
                "style": c.style,
            }
        )
    return {"path": abs_path, "cells": cells}


def read_xml(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"Diagram not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as handle:
        return {"path": abs_path, "xml": handle.read()}


def write_xml(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    check = validate_xml(opts.get("xml") or "")
    if check is not True:
        raise RuntimeError(f"XML is not well-formed: {check}")
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as handle:
        handle.write(opts["xml"])
    return {"path": abs_path}


def export_diagram_op(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"Diagram not found: {abs_path}")
    if not drawio_available():
        raise RuntimeError("Export needs the draw.io desktop app (not installed).")
    output = export_diagram(
        abs_path,
        opts["format"],
        border=opts.get("border") if opts.get("border") is not None else 10,
        scale=opts.get("scale"),
        transparent=bool(opts.get("transparent")),
        layout=opts.get("layout"),
    )
    return {"path": abs_path, "output": output}


def open_diagram(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"Diagram not found: {abs_path}")
    opened = open_diagram_in_editor(abs_path)
    return {"path": abs_path, "opened": opened}


def layout_diagram(opts: Dict[str, Any], task_id: str = "default") -> Dict[str, Any]:
    abs_path = _abs(opts["path"], task_id)
    if not os.path.isfile(abs_path):
        raise RuntimeError(f"Diagram not found: {abs_path}")
    layout = opts["layout"]
    if layout == "layered":
        diagram = _load_diagram(abs_path)
        apply_layered_layout(diagram.pages[0] if diagram.pages else empty_page(), "vertical")
        _save_diagram(abs_path, diagram)
    else:
        preset = layout[4:] if layout.startswith("elk:") else layout
        if not drawio_available():
            raise RuntimeError(f"Layout '{layout}' needs the draw.io desktop CLI (not installed).")
        apply_layout(abs_path, preset)
    return {"path": abs_path, "layout": layout}


def cli_available() -> bool:
    return drawio_available()


def detected_cli_path() -> Optional[str]:
    return find_drawio()
