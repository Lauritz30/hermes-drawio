"""Test support: load the plugin exactly like Hermes's loader and provide fakes.

Hermes imports a directory plugin as ``hermes_plugins.<slug>`` with the plugin directory as the
package path, so the tests reproduce that shape instead of relying on a friendly directory name
(``hermes-drawio`` is not importable as-is).
"""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
NS_PARENT = "hermes_plugins"
MODULE_NAME = f"{NS_PARENT}.hermes_drawio"


def load_plugin(name: str = MODULE_NAME):
    """Import the plugin directory as a package (cached, like the real loader)."""
    if name in sys.modules:
        return sys.modules[name]
    if NS_PARENT not in sys.modules:
        namespace = types.ModuleType(NS_PARENT)
        namespace.__path__ = []  # type: ignore[attr-defined]
        namespace.__package__ = NS_PARENT
        sys.modules[NS_PARENT] = namespace
    spec = importlib.util.spec_from_file_location(
        name, PLUGIN_ROOT / "__init__.py", submodule_search_locations=[str(PLUGIN_ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = name
    module.__path__ = [str(PLUGIN_ROOT)]  # type: ignore[attr-defined]
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeCtx:
    """Stand-in for Hermes's ``PluginContext``, recording what ``register(ctx)`` wired up."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = dict(config or {})
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.cli_commands: Dict[str, Dict[str, Any]] = {}
        self.skills: Dict[str, Path] = {}

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        self.config[key] = value

    def register_tool(self, name: str, toolset: str, schema: dict, handler: Callable, **kwargs: Any):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kwargs}

    def register_hook(self, hook_name: str, callback: Callable):
        self.hooks.setdefault(hook_name, []).append(callback)

    def register_command(self, name: str, handler: Callable, description: str = "", **kwargs: Any):
        self.commands[name] = {"handler": handler, "description": description, **kwargs}

    def register_cli_command(self, name: str, help: str = "", setup_fn: Callable = None, handler_fn: Callable = None, **kwargs: Any):  # noqa: A002
        self.cli_commands[name] = {"help": help, "setup_fn": setup_fn, "handler_fn": handler_fn}

    def register_skill(self, name: str, path: Any):
        self.skills[name] = Path(path)


def parse_provides_tools(manifest_text: str) -> List[str]:
    """Read the ``provides_tools`` list out of ``plugin.yaml`` without a YAML dependency."""
    names: List[str] = []
    inside = False
    for line in manifest_text.splitlines():
        if re.match(r"^provides_tools:\s*$", line):
            inside = True
            continue
        if inside:
            match = re.match(r"^\s+-\s+(\S+)\s*$", line)
            if match:
                names.append(match.group(1))
            elif line.strip() and not line.startswith(" "):
                break
    return names


def iter_skill_files() -> Iterable[Path]:
    return sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
