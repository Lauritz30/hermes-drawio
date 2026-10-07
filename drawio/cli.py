"""draw.io desktop CLI integration (port of pi-drawio's cli.ts).

Binary detection, PNG/SVG/PDF export, ELK/libavoid layout passes, and opening files in the editor.
None of this touches an MCP server — everything is local.
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import urllib.parse
import zlib
from dataclasses import dataclass
from typing import List, Optional

from .settings import drawio_path_override


@dataclass
class RunResult:
    stdout: str
    stderr: str
    code: int


def find_drawio() -> Optional[str]:
    """Locate the draw.io desktop CLI binary, or ``None`` if not installed."""
    candidates: List[str] = []
    override = drawio_path_override()
    if override:
        candidates.append(override)
    env_path = os.environ.get("DRAWIO_PATH")
    if env_path:
        candidates.append(env_path)
    if sys.platform == "darwin":
        candidates.append("/Applications/draw.io.app/Contents/MacOS/draw.io")
    elif sys.platform == "win32":
        candidates.append(r"C:\Program Files\draw.io\draw.io.exe")
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "draw.io", "draw.io.exe"))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    names = ["draw.io.exe", "drawio.exe"] if sys.platform == "win32" else ["drawio", "draw.io"]
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        for name in names:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return path
    return None


def drawio_available() -> bool:
    return find_drawio() is not None


def run_drawio(args: List[str], cwd: Optional[str] = None, timeout: int = 120) -> RunResult:
    binary = find_drawio()
    if not binary:
        raise RuntimeError(
            "draw.io desktop CLI not found. Install draw.io (diagrams.net) desktop app "
            "or set DRAWIO_PATH. Without it you can still create/edit/open .drawio files, "
            "but PNG/SVG/PDF export and ELK/libavoid layout are unavailable."
        )
    try:
        proc = subprocess.run(
            [binary] + args, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return RunResult(stdout=proc.stdout or "", stderr=proc.stderr or "", code=proc.returncode)
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        return RunResult(stdout=stdout or "", stderr=error.stderr or "", code=124)
    except OSError as error:
        return RunResult(stdout="", stderr=str(error), code=1)


def export_diagram(
    input_abs: str,
    fmt: str,
    border: int = 10,
    scale: Optional[float] = None,
    transparent: bool = False,
    layout: Optional[str] = None,
) -> str:
    """Export to png/svg/pdf (XML embedded, so the output stays editable). Returns the output path."""
    out = f"{input_abs}.{fmt}"
    args = ["-x", "-f", fmt, "-e", "-b", str(border)]
    if scale:
        args += ["-s", str(scale)]
    if transparent and fmt == "png":
        args.append("-t")
    if layout:
        args += ["--layout", layout]
    args += ["-o", out, input_abs]

    result = run_drawio(args)
    if not os.path.isfile(out):
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"draw.io export failed (no output file). {detail}".strip())
    return out


def apply_layout(input_abs: str, layout: str) -> None:
    """Run a layout pass in place: ``drawio -x -f xml --layout <layout> -o f f``."""
    result = run_drawio(["-x", "-f", "xml", "--layout", layout, "-o", input_abs, input_abs])
    if result.code != 0 or not os.path.isfile(input_abs):
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"draw.io layout '{layout}' failed. {detail}".strip())


def open_path(path: str) -> None:
    """Open a path (file or URL) in the OS default handler, detached."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(
                ["open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        elif sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/c", "start", "", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError:
        pass


def _encode_uri_component(value: str) -> str:
    """Equivalent of JavaScript's ``encodeURIComponent``."""
    return urllib.parse.quote(value, safe="-_.!~*'()")


def drawio_browser_url(xml: str) -> str:
    """Build a draw.io web-editor URL that opens the given diagram XML directly.

    Uses the same ``#R`` encoding as draw.io's own "Publish > Link" URLs:
    URL-encode → raw DEFLATE → base64, then URL-encode the result.
    """
    encoded = _encode_uri_component(xml)
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = compressor.compress(encoded.encode("utf-8")) + compressor.flush()
    return "https://app.diagrams.net/#R" + urllib.parse.quote(
        base64.b64encode(data).decode("ascii"), safe=""
    )


def open_diagram_in_browser(path: str) -> None:
    with open(path, "r", encoding="utf-8") as handle:
        xml = handle.read()
    open_path(drawio_browser_url(xml))


def open_diagram_in_editor(path: str) -> str:
    """Open a .drawio file in the desktop app, falling back to the browser. Returns how it opened."""
    binary = find_drawio()
    if not binary:
        open_diagram_in_browser(path)
        return "browser"
    try:
        subprocess.Popen(
            [binary, path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass
    return "desktop"
