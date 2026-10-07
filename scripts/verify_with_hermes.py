#!/usr/bin/env python3
"""End-to-end check against a REAL Hermes install.

Everything else in ``tests/`` runs against fakes. This script instead:

1. builds a throwaway ``HERMES_HOME``,
2. installs this plugin into it the documented way (symlink + ``plugins.enabled``),
3. loads it through Hermes's own ``PluginManager`` (real discovery, real import),
4. dispatches tool calls through ``model_tools.handle_function_call`` — the real path the model
   uses,
5. runs the plugin's real CLI command through the ``hermes`` binary.

Run it with the interpreter of your Hermes install, from the repo root:

    ~/.hermes/hermes-agent/venv/bin/python scripts/verify_with_hermes.py

Exits non-zero and prints the offending output when any check fails.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
PLUGIN_NAME = PLUGIN_DIR.name

# Child process: dispatch tool calls through Hermes's real handler.
PHASE_SCRIPT = textwrap.dedent(
    """
    import json
    import sys

    import model_tools  # noqa: F401 - importing it is what runs plugin discovery
    from model_tools import handle_function_call

    name = sys.argv[1]
    payload = json.loads(sys.argv[2])
    print("RESULT:" + handle_function_call(name, payload, task_id="e2e"))
    """
)


def build_home() -> Path:
    home = Path(tempfile.mkdtemp(prefix="hermes-drawio-e2e-"))
    (home / "plugins").mkdir()
    os.symlink(PLUGIN_DIR, home / "plugins" / PLUGIN_NAME)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - " + PLUGIN_NAME + "\n", encoding="utf-8"
    )
    return home


def child_env(home: Path) -> dict:
    env = dict(os.environ)
    env["HERMES_HOME"] = str(home)
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    return env


def run_phase(home: Path, name: str, payload: dict) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", PHASE_SCRIPT, name, json.dumps(payload)],
        capture_output=True,
        text=True,
        env=child_env(home),
        # NOT the plugin directory: Python puts cwd on sys.path, and this repo must not shadow
        # Hermes's own top-level modules.
        cwd=str(home),
    )
    if proc.returncode != 0:
        raise SystemExit(f"[{name}] dispatch failed:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()


def check(label: str, condition: bool, detail: str) -> None:
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        raise SystemExit(f"check failed: {label}\n{detail}")


def main() -> int:
    print(f"plugin: {PLUGIN_DIR}")
    home = build_home()
    try:
        print("1. real discovery + plugin list")
        listing = subprocess.run(
            ["hermes", "plugins", "list", "--plain", "--no-bundled"],
            capture_output=True,
            text=True,
            env=child_env(home),
        )
        check(
            "`hermes plugins list` sees the plugin as enabled",
            PLUGIN_NAME in listing.stdout and "enabled" in listing.stdout,
            listing.stdout + listing.stderr,
        )

        print("2. tool dispatch: drawio_status")
        status_out = run_phase(home, "drawio_status", {})
        check(
            "drawio_status returns ok with the shape/palette summary",
            '"ok": true' in status_out.replace("'", '"') and "Shapes:" in status_out,
            status_out,
        )

        print("3. tool dispatch: drawio_create_diagram (no side effects: open=false)")
        diagram = str(home / "e2e.drawio")
        create_out = run_phase(
            home,
            "drawio_create_diagram",
            {
                "path": diagram,
                "title": "E2E",
                "nodes": [
                    {"id": "a", "label": "Start", "shape": "terminator"},
                    {"id": "b", "label": "End", "shape": "terminator"},
                ],
                "edges": [{"source": "a", "target": "b"}],
                "open": False,
            },
        )
        check(
            "drawio_create_diagram reports success",
            '"ok": true' in create_out.replace("'", '"') and "2 node(s)" in create_out,
            create_out,
        )
        check(
            "the .drawio file was written to disk",
            Path(diagram).is_file() and 'host="hermes-drawio"' in Path(diagram).read_text(encoding="utf-8"),
            diagram,
        )

        print("4. real CLI command (`hermes drawio status`)")
        cli = subprocess.run(
            ["hermes", "drawio", "status"], capture_output=True, text=True, env=child_env(home)
        )
        check(
            "the CLI tree runs and prints draw.io status",
            "draw.io" in cli.stdout and cli.returncode == 0,
            cli.stdout + cli.stderr,
        )

        print("\nAll end-to-end checks passed.")
        return 0
    finally:
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
