"""Tool schemas — what the LLM sees (port of pi-drawio's TypeBox definitions)."""

from __future__ import annotations

from typing import Any, Dict

DIRECTION: Dict[str, Any] = {
    "type": "string",
    "enum": ["vertical", "horizontal"],
    "description": "Flow direction for the built-in layered layout.",
}

FORMAT: Dict[str, Any] = {
    "type": "string",
    "enum": ["png", "svg", "pdf"],
    "description": "Export format. XML is embedded so the export stays editable in draw.io.",
}

LAYOUT: Dict[str, Any] = {
    "type": "string",
    "description": (
        'Layout to apply. "layered" (default, built-in, no CLI) | "none" (use explicit x/y) | '
        '"elk:verticalFlow" | "elk:horizontalFlow" | "elk:verticalTree" | "elk:horizontalTree" | '
        '"elk:organic" | "libavoid" (needs draw.io desktop CLI).'
    ),
}

NODE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Stable node id (e.g. 'start', 'approve'). Must be unique; referenced by edges.",
        },
        "label": {"type": "string", "description": "Node text label."},
        "shape": {
            "type": "string",
            "description": (
                "Shape name: rounded, rectangle, ellipse, terminator, diamond, parallelogram, "
                "hexagon, document, database, cloud, text."
            ),
        },
        "style": {"type": "string", "description": "Raw mxGraph style string override (advanced)."},
        "lane": {"type": "string", "description": "Lane id or name this node belongs to (for swimlanes)."},
        "role": {
            "type": "string",
            "description": "Role key (e.g. 'customer', 'backend') used to derive a stable color.",
        },
        "fillColor": {"type": "string", "description": "Hex fill override, e.g. '#DAE8FC'."},
        "strokeColor": {"type": "string", "description": "Hex border override, e.g. '#6C8EBF'."},
        "x": {"type": "number", "description": "Explicit x (only used when layout is 'none')."},
        "y": {"type": "number", "description": "Explicit y (only used when layout is 'none')."},
        "width": {"type": "number", "description": "Width in px."},
        "height": {"type": "number", "description": "Height in px."},
    },
}

EDGE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Optional edge id."},
        "source": {"type": "string", "description": "Source node id."},
        "target": {"type": "string", "description": "Target node id."},
        "label": {"type": "string", "description": "Edge label."},
        "style": {"type": "string", "description": "Raw mxGraph edge style override (advanced)."},
        "dashed": {"type": "boolean", "description": "Dashed connector without arrowhead."},
        "arrow": {"type": "boolean", "description": "Show arrowhead (default true)."},
    },
    "required": ["source", "target"],
}

LANE: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Optional lane id (referenced by node.lane)."},
        "name": {"type": "string", "description": "Lane header title."},
        "role": {
            "type": "string",
            "description": "Role key; determines the lane color (one role = one color).",
        },
        "color": {"type": "string", "description": "Hex fill override for this lane."},
        "nodes": {"type": "array", "items": NODE, "description": "Nodes to place inside this lane."},
    },
}

NODE_ARRAY: Dict[str, Any] = {"type": "array", "items": NODE}
EDGE_ARRAY: Dict[str, Any] = {"type": "array", "items": EDGE}
LANE_ARRAY: Dict[str, Any] = {"type": "array", "items": LANE}

CREATE_DIAGRAM: Dict[str, Any] = {
    "name": "drawio_create_diagram",
    "description": (
        "Create a new .drawio diagram (flowchart, process flow, architecture, etc.) and write it to "
        "a local file. Use lanes[] to make swimlanes (one lane per role/actor). Assign each node a "
        "`lane` (id or name) and optionally a `role`. Roles and lanes are auto-colored: one role = "
        "one color, each lane gets a distinct color. Nodes reference edges via their id (give nodes "
        "stable ids). After creation the file is opened in the draw.io desktop app (or in the browser "
        "if the app is not installed); if `exportFormat` is set, a PNG/SVG/PDF is also produced and "
        "you SHOULD read it back (via the read tool) to visually verify the layout."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Output file path, e.g. 'diagrams/login-flow.drawio'."},
            "title": {"type": "string", "description": "Diagram/page title."},
            "nodes": NODE_ARRAY,
            "edges": EDGE_ARRAY,
            "lanes": LANE_ARRAY,
            "direction": DIRECTION,
            "layout": LAYOUT,
            "open": {"type": "boolean", "description": "Open in draw.io after (default true)."},
            "exportFormat": FORMAT,
            "border": {"type": "number", "description": "Export border width in px (default 10)."},
            "scale": {"type": "number", "description": "Export scale, e.g. 2 for 2x resolution PNG."},
        },
        "required": ["path"],
    },
}

ADD_CELLS: Dict[str, Any] = {
    "name": "drawio_add_cells",
    "description": (
        "Add nodes, edges, and/or lanes to an existing .drawio diagram, then re-run the built-in "
        "layered layout. Reference existing nodes by id in edges. New lanes can be created via "
        "lanes[] or referenced by name in node.lane."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "nodes": NODE_ARRAY,
            "edges": EDGE_ARRAY,
            "lanes": LANE_ARRAY,
            "direction": DIRECTION,
            "layout": LAYOUT,
            "open": {"type": "boolean", "description": "Open in draw.io after (default true)."},
        },
        "required": ["path"],
    },
}

UPDATE_CELLS: Dict[str, Any] = {
    "name": "drawio_update_cells",
    "description": "Update labels, styles, colors, shapes, or positions of existing cells by id.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "cells": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Cell id to update."},
                        "label": {"type": "string"},
                        "style": {"type": "string", "description": "Raw mxGraph style override."},
                        "shape": {
                            "type": "string",
                            "description": "Change shape (rounded, rectangle, ellipse, diamond, ...).",
                        },
                        "fillColor": {"type": "string"},
                        "strokeColor": {"type": "string"},
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "width": {"type": "number"},
                        "height": {"type": "number"},
                    },
                    "required": ["id"],
                },
            },
            "layout": {
                "type": "string",
                "description": "Re-run layout after update (default: layered; pass 'none' to keep positions).",
            },
        },
        "required": ["path", "cells"],
    },
}

DELETE_CELLS: Dict[str, Any] = {
    "name": "drawio_delete_cells",
    "description": "Delete cells by id. Edges connected to a deleted node are removed too.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "ids": {"type": "array", "items": {"type": "string"}, "description": "Cell ids to delete."},
            "layout": {
                "type": "string",
                "description": "Re-run layout after delete (default: layered; pass 'none' to skip).",
            },
        },
        "required": ["path", "ids"],
    },
}

LIST_CELLS: Dict[str, Any] = {
    "name": "drawio_list_cells",
    "description": (
        "List all cells (id, kind, label, parent, geometry, style) in a .drawio diagram so you know "
        "what exists before editing."
    ),
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path to the .drawio file."}},
        "required": ["path"],
    },
}

READ_XML: Dict[str, Any] = {
    "name": "drawio_read_xml",
    "description": "Return the raw .drawio XML (escape hatch for advanced edits).",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path to the .drawio file."}},
        "required": ["path"],
    },
}

WRITE_XML: Dict[str, Any] = {
    "name": "drawio_write_xml",
    "description": (
        "Overwrite a .drawio file with raw mxGraphModel XML (escape hatch). Validates well-formedness "
        "first."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "xml": {"type": "string", "description": "Full mxfile/mxGraphModel XML."},
        },
        "required": ["path", "xml"],
    },
}

EXPORT: Dict[str, Any] = {
    "name": "drawio_export",
    "description": (
        "Export a .drawio diagram to PNG/SVG/PDF via the draw.io desktop CLI (XML embedded, so it "
        "stays editable). After exporting, read the PNG/SVG back to visually verify the diagram."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "format": {
                "type": "string",
                "enum": ["png", "svg", "pdf"],
                "description": "Output format.",
            },
            "border": {"type": "number", "description": "Border width in px (default 10)."},
            "scale": {"type": "number", "description": "Scale, e.g. 2 for 2x."},
            "transparent": {"type": "boolean", "description": "Transparent background (PNG only)."},
            "layout": {
                "type": "string",
                "description": "Optional ELK preset or libavoid to apply before export.",
            },
        },
        "required": ["path", "format"],
    },
}

OPEN: Dict[str, Any] = {
    "name": "drawio_open",
    "description": (
        "Open a .drawio file in the draw.io desktop app, falling back to the browser (draw.io web "
        "editor) if the desktop app is not installed."
    ),
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path to the file to open."}},
        "required": ["path"],
    },
}

LAYOUT_DIAGRAM: Dict[str, Any] = {
    "name": "drawio_layout",
    "description": (
        "Re-layout a diagram: built-in 'layered', or an ELK preset / 'libavoid' via the draw.io "
        "desktop CLI."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the .drawio file."},
            "layout": {
                "type": "string",
                "description": (
                    "'layered' (built-in) | 'elk:verticalFlow' | 'elk:horizontalFlow' | "
                    "'elk:organic' | 'libavoid' ..."
                ),
            },
        },
        "required": ["path", "layout"],
    },
}

STATUS: Dict[str, Any] = {
    "name": "drawio_status",
    "description": (
        "Report whether the draw.io desktop CLI is available and list the shape names and color "
        "palette this extension supports."
    ),
    "parameters": {"type": "object", "properties": {}},
}

TOOL_SCHEMAS = (
    CREATE_DIAGRAM,
    ADD_CELLS,
    UPDATE_CELLS,
    DELETE_CELLS,
    LIST_CELLS,
    READ_XML,
    WRITE_XML,
    EXPORT,
    OPEN,
    LAYOUT_DIAGRAM,
    STATUS,
)

__all__ = [
    "ADD_CELLS",
    "CREATE_DIAGRAM",
    "DELETE_CELLS",
    "EXPORT",
    "LAYOUT_DIAGRAM",
    "LIST_CELLS",
    "OPEN",
    "READ_XML",
    "STATUS",
    "TOOL_SCHEMAS",
    "UPDATE_CELLS",
    "WRITE_XML",
]
