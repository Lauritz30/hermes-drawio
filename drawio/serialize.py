"""IR → native .drawio (mxGraphModel) XML (port of pi-drawio's serialize.ts)."""

from __future__ import annotations

from .model import Diagram, Cell

_RESERVED_ATTRS = frozenset({"id", "value", "style", "vertex", "edge", "parent", "source", "target"})


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "&#xa;")
        .replace("\r", "&#xd;")
        .replace("\t", "&#x9;")
    )


def _fmt(n: float) -> str:
    """Round to 2 decimals and strip trailing zeros, matching the TS serializer's String()."""
    v = round(float(n) * 100) / 100
    if v == 0:
        return "0"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def _cell_to_xml(cell: Cell) -> str:
    attrs = [f'id="{_esc(cell.id)}"']
    if cell.value is not None:
        attrs.append(f'value="{_esc(cell.value)}"')
    if cell.style:
        attrs.append(f'style="{_esc(cell.style)}"')
    if cell.vertex:
        attrs.append('vertex="1"')
    if cell.edge:
        attrs.append('edge="1"')
    if cell.parent is not None:
        attrs.append(f'parent="{_esc(cell.parent)}"')
    if cell.source is not None:
        attrs.append(f'source="{_esc(cell.source)}"')
    if cell.target is not None:
        attrs.append(f'target="{_esc(cell.target)}"')
    for key, value in cell.extra_attrs.items():
        if key not in _RESERVED_ATTRS:
            attrs.append(f'{_esc(key)}="{_esc(value)}"')

    inner = ""
    geo = cell.geometry

    if cell.edge:
        points = "".join(
            f'<mxPoint x="{_fmt(p.x)}" y="{_fmt(p.y)}" />' for p in (geo.points if geo else [])
        )
        inner = (
            f'<mxGeometry relative="1" as="geometry"><Array as="points">{points}</Array></mxGeometry>'
            if points
            else '<mxGeometry relative="1" as="geometry" />'
        )
    elif geo:
        parts = []
        if geo.x is not None:
            parts.append(f'x="{_fmt(geo.x)}"')
        if geo.y is not None:
            parts.append(f'y="{_fmt(geo.y)}"')
        if geo.width is not None:
            parts.append(f'width="{_fmt(geo.width)}"')
        if geo.height is not None:
            parts.append(f'height="{_fmt(geo.height)}"')
        if geo.relative:
            parts.append('relative="1"')
        parts.append('as="geometry"')
        inner = f'<mxGeometry {" ".join(parts)} />'

    return f'<mxCell {" ".join(attrs)}>{inner}</mxCell>' if inner else f'<mxCell {" ".join(attrs)} />'


def serialize_diagram(diagram: Diagram) -> str:
    pages = []
    for page in diagram.pages:
        cells = "\n".join(_cell_to_xml(c) for c in page.cells)
        model = (
            '<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" guides="1" tooltips="1" '
            'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" '
            'pageHeight="1100" math="0" shadow="0">\n'
            "  <root>\n"
            + cells
            + "\n  </root>\n</mxGraphModel>"
        )
        pages.append(f'<diagram id="{_esc(page.id)}" name="{_esc(page.name)}">\n{model}\n</diagram>')

    diagrams = "\n".join(pages)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="hermes-drawio" agent="hermes" version="24.0.0">\n'
        + diagrams
        + "\n</mxfile>\n"
    )
