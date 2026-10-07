"""Native .drawio XML → IR (port of pi-drawio's parse.ts, using the stdlib xml.etree).

Decodes draw.io's compressed ``<diagram>`` bodies (base64 of ``deflateRaw(encodeURIComponent(xml))``)
with ``zlib`` and preserves unknown cell attributes across round-trips.
"""

from __future__ import annotations

import base64
import math
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from typing import List, Optional

from .model import Cell, CellGeometry, Diagram, Page, Point

_RESERVED_ATTRS = frozenset({"id", "value", "style", "vertex", "edge", "parent", "source", "target"})


def _num(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except ValueError:
        return None
    return n if math.isfinite(n) else None


def _to_point(elem: ET.Element) -> Optional[Point]:
    x = _num(elem.get("x"))
    y = _num(elem.get("y"))
    if x is None or y is None:
        return None
    return Point(x=x, y=y)


def _parse_geometry(geo: Optional[ET.Element]) -> Optional[CellGeometry]:
    if geo is None:
        return None
    geometry = CellGeometry()
    x = _num(geo.get("x"))
    y = _num(geo.get("y"))
    w = _num(geo.get("width"))
    h = _num(geo.get("height"))
    if x is not None:
        geometry.x = x
    if y is not None:
        geometry.y = y
    if w is not None:
        geometry.width = w
    if h is not None:
        geometry.height = h
    relative = geo.get("relative")
    if relative in ("1", "true"):
        geometry.relative = True

    arr = geo.find("Array")
    if arr is not None:
        points: List[Point] = []
        for mp in arr.findall("mxPoint"):
            pt = _to_point(mp)
            if pt is not None:
                points.append(pt)
        if points:
            geometry.points = points
    return geometry


def _cell_from_element(elem: ET.Element) -> Cell:
    cell_id = elem.get("id") or "cell-%08x" % (id(elem) & 0xFFFFFFFF)
    cell = Cell(id=cell_id)
    if elem.get("value") is not None:
        cell.value = elem.get("value")
    if elem.get("style") is not None:
        cell.style = elem.get("style")
    if elem.get("vertex") == "1":
        cell.vertex = True
    if elem.get("edge") == "1":
        cell.edge = True
    if elem.get("parent") is not None:
        cell.parent = elem.get("parent")
    if elem.get("source") is not None:
        cell.source = elem.get("source")
    if elem.get("target") is not None:
        cell.target = elem.get("target")

    for key, value in elem.attrib.items():
        if key not in _RESERVED_ATTRS:
            cell.extra_attrs[key] = value

    geo = _parse_geometry(elem.find("mxGeometry"))
    if geo is not None:
        cell.geometry = geo
    return cell


def _extract_cells(model: ET.Element) -> List[Cell]:
    root = model.find("root")
    if root is None:
        return []
    return [_cell_from_element(c) for c in root.findall("mxCell")]


def _decode_body(text: Optional[str]) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if "<" in t:
        return t  # already raw XML
    try:
        raw = base64.b64decode(t)
        decompressed = zlib.decompress(raw, -15)
        return urllib.parse.unquote(decompressed.decode("latin1"))
    except Exception:
        return t


def validate_xml(xml: str):
    """Return ``True`` when well-formed, otherwise an error string."""
    try:
        ET.fromstring(xml)
        return True
    except ET.ParseError as error:
        return str(error)


def parse_diagram(xml: str) -> Diagram:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError(f"Failed to parse .drawio XML: {error}") from error

    pages: List[Page] = []

    # Bare <mxGraphModel> (draw.io also accepts this).
    if root.tag == "mxGraphModel":
        pages.append(Page(id="page-1", name="Page-1", cells=_extract_cells(root)))
        return Diagram(pages=pages)

    if root.tag != "mxfile":
        raise ValueError("Not a .drawio file: no <mxfile> or <mxGraphModel> found")

    index = 0
    for diagram_elem in root.findall("diagram"):
        index += 1
        page_id = diagram_elem.get("id") or f"page-{index}"
        page_name = diagram_elem.get("name") or page_id
        cells: List[Cell] = []

        model = diagram_elem.find("mxGraphModel")
        if model is not None:
            cells = _extract_cells(model)
        else:
            decoded = _decode_body(diagram_elem.text)
            if "<" in decoded:
                try:
                    sub = ET.fromstring(decoded)
                    if sub.tag == "mxGraphModel":
                        cells = _extract_cells(sub)
                except ET.ParseError:
                    cells = []

        pages.append(Page(id=page_id, name=page_name, cells=cells))

    return Diagram(pages=pages)
