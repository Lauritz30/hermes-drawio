# hermes-drawio

draw.io diagram integration for [Hermes Agent](https://github.com/nousresearch/hermes) — a Python
port of [`pi-drawio`](https://github.com/Lauritz30/pi-drawio). Create and edit native `.drawio`
(mxGraphModel) files **locally, no MCP server**.

It builds/edits diagrams through a small intermediate representation, auto-colors roles and
swimlanes, applies layered or ELK layout, and exports PNG/SVG/PDF via the draw.io desktop CLI.

## Features

- **11 tools** (`drawio_*`) for create / add / update / delete / list / read-write raw XML / export / open / layout / status.
- **Role-based auto-coloring** — one role = one color, each swimlane gets a distinct color, nodes inherit their lane's color.
- **Built-in layered layout** (no CLI needed) + **ELK / libavoid** via the draw.io desktop CLI.
- **PNG / SVG / PDF export** (XML embedded, so exports stay editable in draw.io).
- **Open in the draw.io desktop app**, with automatic browser fallback (`app.diagrams.net`) when the app is not installed.
- A `/drawio` slash command and a `hermes drawio` CLI command.
- A bundled `drawio-diagrams` skill teaching the model the coloring rules and the create→export→verify loop.

## Requirements

- Python ≥ 3.10 (stdlib only — no runtime dependencies).
- **Optional:** the [draw.io desktop app](https://www.diagrams.net/) for PNG/SVG/PDF export and
  ELK/libavoid layout. Without it you can still create/edit/open `.drawio` files (opening falls
  back to the browser).

## Install

From the repo root, symlink into Hermes's plugins directory and enable it:

```bash
mkdir -p ~/.hermes/plugins
ln -s "$(pwd)" ~/.hermes/plugins/hermes-drawio
hermes plugins enable hermes-drawio
```

Then restart Hermes (or let it re-discover plugins). Verify with:

```bash
hermes plugins doctor . --ci
```

### Config (optional)

Set the draw.io CLI path in `~/.hermes/config.yaml`:

```yaml
plugins:
  entries:
    hermes-drawio:
      settings:
        drawio_path: /Applications/draw.io.app/Contents/MacOS/draw.io
```

Empty (the default) means "auto-detect": `DRAWIO_PATH` env var, then the per-OS install location,
then `PATH`.

## Tools

| Tool | What it does |
|---|---|
| `drawio_create_diagram` | Create a new diagram (flowchart, process flow, architecture, swimlanes). |
| `drawio_add_cells` | Add nodes/edges/lanes to an existing diagram. |
| `drawio_update_cells` | Change labels, styles, colors, shapes, positions. |
| `drawio_delete_cells` | Remove cells (connected edges are removed too). |
| `drawio_list_cells` | List every cell (id, kind, label, parent, geometry, style). |
| `drawio_read_xml` | Return raw `.drawio` XML (escape hatch). |
| `drawio_write_xml` | Overwrite with raw XML (well-formedness checked). |
| `drawio_export` | Export PNG/SVG/PDF via the desktop CLI. |
| `drawio_open` | Open in the desktop app (browser fallback). |
| `drawio_layout` | Re-layout: `layered`, `elk:*`, or `libavoid`. |
| `drawio_status` | Report CLI availability + shape names + palette. |

## Example

```json
{
  "path": "diagrams/order-process.drawio",
  "title": "Order process",
  "lanes": [
    { "id": "customer", "name": "Customer", "role": "customer",
      "nodes": [
        { "id": "start", "label": "Place order", "shape": "terminator" },
        { "id": "receive", "label": "Receive goods", "shape": "rounded" }
      ] },
    { "id": "backend", "name": "Backend", "role": "backend",
      "nodes": [
        { "id": "validate", "label": "Validate order", "shape": "rounded" },
        { "id": "ship", "label": "Ship order", "shape": "rounded" }
      ] }
  ],
  "edges": [
    { "source": "start", "target": "validate" },
    { "source": "validate", "target": "ship" },
    { "source": "ship", "target": "receive" }
  ],
  "exportFormat": "png"
}
```

## Development

```bash
# Unit tests (stdlib unittest, no Hermes required)
python3 -m unittest discover -v

# End-to-end check against a real Hermes install
~/.hermes/hermes-agent/venv/bin/python scripts/verify_with_hermes.py

# Admission check
hermes plugins doctor . --ci
```

## Project layout

```
__init__.py            register(ctx): tools + /drawio command + hermes drawio CLI + skill
schemas.py             tool schemas (what the LLM sees)
drawio/
  model.py             IR (Cell, Page, Diagram, RoleColor, ShapeDef)
  parse.py             .drawio XML → IR (incl. zlib-compressed <diagram> bodies)
  serialize.py         IR → .drawio XML
  colors.py            role/lane palette + stable hash → color mapping
  styles.py            shape/edge style strings + color merging
  layout.py            built-in layered auto-layout (swimlane-aware)
  cli.py               draw.io CLI detection, export, ELK layout, open (desktop→browser)
  engine.py            high-level ops shared by the tools
  tools/               guarded handlers + HANDLERS map
skills/drawio-diagrams/SKILL.md
tests/                 unit tests (fakes)
scripts/verify_with_hermes.py
```

## License

MIT © Lauritz30
