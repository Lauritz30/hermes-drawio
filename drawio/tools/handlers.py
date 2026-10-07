"""Tool handlers — what runs when the model calls a draw.io tool.

Each handler is ``guarded``: failures become ``{"ok": false, "error": ...}`` JSON instead of an
exception. Handlers receive the tool's ``args`` dict plus Hermes's signature-inspected context
kwargs (``task_id`` is used to anchor relative paths to the task's terminal cwd).
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .. import engine
from ..colors import PALETTE
from ..styles import SHAPES
from .shared import guarded, ok_result


def _where(opened: str) -> str:
    return "the draw.io desktop app" if opened == "desktop" else "the browser (draw.io web editor)"


@guarded
def drawio_create_diagram(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.create_diagram(dict(args), task_id=task_id or "default")
    lines = [
        f"Created {r['nodes']} node(s), {r['edges']} edge(s), {r['lanes']} lane(s).",
        f"File: {r['path']}",
    ]
    if r.get("opened"):
        lines.append(f"Opened in {_where(r['opened'])}.")
    if r.get("exported"):
        lines.append(f"Exported: {r['exported']} — read it back to verify the layout.")
    if not r.get("drawioCli"):
        lines.append(
            "draw.io desktop CLI not detected; PNG/SVG/PDF export and ELK layout are unavailable."
        )
    return ok_result("\n".join(lines), r)


@guarded
def drawio_add_cells(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.add_cells(dict(args), task_id=task_id or "default")
    where = f" Opened in {_where(r['opened'])}." if r.get("opened") else ""
    return ok_result(
        f"Added {r['nodes']} node(s), {r['edges']} edge(s), {r['lanes']} lane(s). "
        f"File: {r['path']}.{where}",
        r,
    )


@guarded
def drawio_update_cells(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.update_cells(dict(args), task_id=task_id or "default")
    return ok_result(f"Updated {r['updated']} cell(s). File: {r['path']}", r)


@guarded
def drawio_delete_cells(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.delete_cells(dict(args), task_id=task_id or "default")
    return ok_result(f"Removed {r['removed']} cell(s). File: {r['path']}", r)


@guarded
def drawio_list_cells(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.list_cells(dict(args), task_id=task_id or "default")
    lines: List[str] = []
    for c in r["cells"]:
        g = c.get("geometry")
        geom = (
            f" ({g.get('x', '?')},{g.get('y', '?')} {g.get('width', '?')}x{g.get('height', '?')})"
            if g
            else ""
        )
        if c["kind"] == "edge":
            extra = f" {c.get('source')}->{c.get('target')}"
        elif c["kind"] == "swimlane":
            extra = " [swimlane]"
        else:
            extra = ""
        label = c.get("label") or ""
        parent = c.get("parent") or ""
        lines.append(
            f"{c['id']} [{c['kind']}]{extra} label=\"{label}\" parent=\"{parent}\"{geom}"
        )
    return ok_result("\n".join(lines) or "(no cells)", r)


@guarded
def drawio_read_xml(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.read_xml(dict(args), task_id=task_id or "default")
    return ok_result(r["xml"], r)


@guarded
def drawio_write_xml(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.write_xml(dict(args), task_id=task_id or "default")
    return ok_result(f"Wrote raw XML to {r['path']}", r)


@guarded
def drawio_export(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.export_diagram_op(dict(args), task_id=task_id or "default")
    return ok_result(f"Exported {r['path']} → {r['output']}. Read it back to verify.", r)


@guarded
def drawio_open(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.open_diagram(dict(args), task_id=task_id or "default")
    return ok_result(f"Opened {r['path']} in {_where(r['opened'])}.", r)


@guarded
def drawio_layout(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    r = engine.layout_diagram(dict(args), task_id=task_id or "default")
    return ok_result(f"Applied layout '{r['layout']}' to {r['path']}", r)


@guarded
def drawio_status(args: Mapping[str, Any], task_id: str = "default", **kwargs: Any) -> str:
    shapes = ", ".join(SHAPES.keys())
    colors = ", ".join(f"{c.name} ({c.fill})" for c in PALETTE)
    cli = engine.cli_available()
    cli_path = engine.detected_cli_path()
    r = {
        "cliAvailable": cli,
        "cliPath": cli_path,
        "shapes": shapes,
        "palette": [{"name": c.name, "fill": c.fill, "stroke": c.stroke} for c in PALETTE],
    }
    return ok_result(
        f"draw.io desktop CLI: {'available (' + cli_path + ')' if cli else 'NOT available — PNG/SVG/PDF export and ELK layout disabled.'}\n"
        f"Shapes: {shapes}\n"
        f"Role colors: {colors}",
        r,
    )


HANDLERS: Dict[str, Any] = {
    "drawio_create_diagram": drawio_create_diagram,
    "drawio_add_cells": drawio_add_cells,
    "drawio_update_cells": drawio_update_cells,
    "drawio_delete_cells": drawio_delete_cells,
    "drawio_list_cells": drawio_list_cells,
    "drawio_read_xml": drawio_read_xml,
    "drawio_write_xml": drawio_write_xml,
    "drawio_export": drawio_export,
    "drawio_open": drawio_open,
    "drawio_layout": drawio_layout,
    "drawio_status": drawio_status,
}

__all__ = ["HANDLERS"]
