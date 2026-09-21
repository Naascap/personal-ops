from __future__ import annotations

import os
from pathlib import Path

from .errors import ConfigError


def default_home() -> Path:
    override = os.environ.get("PERSONAL_OPS_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".personal-ops"


def repo_root(start: Path) -> Path | None:
    for candidate in (start.resolve(), *start.resolve().parents):
        marker = candidate / ".git"
        if marker.is_file() or (marker.is_dir() and (marker / "HEAD").is_file()):
            return candidate
    return None


def require_runtime_outside_repo(data_dir: Path, start: Path | None = None) -> None:
    resolved = data_dir.expanduser().resolve()
    roots: list[Path] = []
    current = repo_root(start or Path.cwd())
    if current is not None:
        roots.append(current)
    nested = repo_root(resolved)
    if nested is not None:
        roots.append(nested)
    for root in set(roots):
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        raise ConfigError(
            f"runtime data directory must be outside the Git repository ({root}); got {resolved}"
        )
