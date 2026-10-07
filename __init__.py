"""hermes-drawio — draw.io diagram integration plugin for Hermes Agent.

The plugin registers the draw.io tools, the ``/drawio`` slash command, a ``hermes drawio`` CLI
command, and the bundled ``drawio-diagrams`` skill. Everything is local: it builds/edits native
``.drawio`` (mxGraphModel) XML and optionally uses the draw.io desktop CLI for ELK layout and
PNG/SVG/PDF export. No MCP server.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict

from . import schemas
from .drawio import engine
from .drawio.settings import set_drawio_path
from .drawio.tools import HANDLERS

logger = logging.getLogger(__name__)

TOOLSET = "drawio"
SKILLS_DIR = Path(__file__).parent / "skills"

__all__ = ["TOOLSET", "register"]


def _schema_map() -> Dict[str, Dict[str, Any]]:
    return {schema["name"]: schema for schema in schemas.TOOL_SCHEMAS}


def _drawio_command(raw_args: str = "") -> str:
    """``/drawio open <file> | export <file> [format] | list <file> | status``."""
    parts = (raw_args or "").strip().split()
    sub = parts[0] if parts else ""
    file = parts[1] if len(parts) > 1 else ""
    try:
        if not sub:
            return "Usage: /drawio open <file> | export <file> [format] | list <file> | status"
        if sub == "status":
            return f"draw.io CLI: {'available' if engine.cli_available() else 'not available'}"
        if not file:
            return "Missing file path."
        if sub == "open":
            r = engine.open_diagram({"path": file})
            return f"Opened {file} in {r['opened']}"
        if sub == "export":
            fmt = parts[2] if len(parts) > 2 else "png"
            r = engine.export_diagram_op({"path": file, "format": fmt})
            return f"Exported → {r['output']}"
        if sub == "list":
            r = engine.list_cells({"path": file})
            return f"{len(r['cells'])} cells in {file}"
        return f"Unknown /drawio subcommand: {sub}"
    except Exception as error:  # noqa: BLE001 - slash commands render the message, not the trace
        return f"drawio: {error}"


def _cli_drawio(args: argparse.Namespace) -> None:
    """``hermes drawio <subcommand>`` handler."""
    action = getattr(args, "drawio_command", None)
    if action == "status":
        path = engine.detected_cli_path()
        if engine.cli_available():
            print(f"draw.io desktop CLI available at {path}")
        else:
            print("draw.io desktop CLI NOT available — PNG/SVG/PDF export and ELK layout disabled.")
    else:
        print("Usage: hermes drawio <status>")


def _setup_cli(subparser: argparse.ArgumentParser) -> None:
    """Build the ``hermes drawio`` argparse tree."""
    subs = subparser.add_subparsers(dest="drawio_command")
    subs.add_parser("status", help="Show whether the draw.io desktop CLI is available")
    subparser.set_defaults(func=_cli_drawio)


def _register_skills(ctx: Any) -> None:
    """Expose ``skills/*/SKILL.md`` as namespaced plugin skills."""
    if not SKILLS_DIR.is_dir():
        return
    for child in sorted(SKILLS_DIR.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            try:
                ctx.register_skill(child.name, skill_md)
            except Exception as error:  # noqa: BLE001 - skills are additive, never fatal
                logger.warning("hermes-drawio: could not register skill %s (%s)", child.name, error)


def register(ctx: Any) -> None:
    """Wire the plugin: tools, slash command, CLI command, bundled skill."""
    set_drawio_path(ctx.get_config("drawio_path", default=""))

    handler_map = dict(HANDLERS)
    schema_map = _schema_map()

    missing_handlers = sorted(set(schema_map) - set(handler_map))
    missing_schemas = sorted(set(handler_map) - set(schema_map))
    if missing_handlers or missing_schemas:
        raise RuntimeError(
            "hermes-drawio: schema/handler mismatch — "
            f"schemas without handlers: {missing_handlers}; handlers without schemas: {missing_schemas}"
        )

    for name, schema in schema_map.items():
        ctx.register_tool(name=name, toolset=TOOLSET, schema=schema, handler=handler_map[name])

    ctx.register_command(
        "drawio",
        handler=_drawio_command,
        description="draw.io helpers: /drawio open <file> | export <file> [format] | list <file> | status",
        args_hint="<file>",
    )

    ctx.register_cli_command(
        name="drawio",
        help="draw.io diagram helpers (hermes-drawio)",
        setup_fn=_setup_cli,
        handler_fn=_cli_drawio,
    )

    _register_skills(ctx)
