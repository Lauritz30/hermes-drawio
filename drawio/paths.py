"""Task-aware path resolution for the plugin's file operations.

Under Hermes, relative paths are anchored to the task's terminal cwd (not the agent process cwd,
which can differ in gateway/worktree sessions). Best-effort: when the internal helper is not
importable (e.g. standalone unit tests), we fall back to the process cwd.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def resolve_file(path: str, task_id: str = "default") -> str:
    """Return *path* as an absolute, normalized path, anchored to the task cwd when relative."""
    try:
        from tools.file_tools_paths import _resolve_path_for_task  # type: ignore

        return str(_resolve_path_for_task(path, task_id))
    except Exception:
        p = Path(path).expanduser()
        if p.is_absolute():
            return str(p.resolve())
        return str((Path.cwd() / p).resolve())


def resolve_dir(path: str, task_id: str = "default") -> str:
    """Resolve a directory path the same way (used for mkdir parents)."""
    return resolve_file(path, task_id)


def resolve_cwd(task_id: str = "default") -> str:
    """Return the absolute base directory for the task (fallback: process cwd)."""
    try:
        from tools.file_tools_paths import _resolve_base_dir  # type: ignore

        return str(_resolve_base_dir(task_id))
    except Exception:
        try:
            return str(Path.cwd().resolve())
        except OSError:
            return os.path.expanduser("~")


def optional_abs(path: Optional[str], task_id: str = "default") -> Optional[str]:
    return resolve_file(path, task_id) if path else None
