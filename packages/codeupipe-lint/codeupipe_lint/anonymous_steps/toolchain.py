"""Finding and running the external parsers some analyzers use (go, bun/node)."""

import hashlib
import os
import shutil
import tempfile
from typing import Iterable, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
# The monorepo root, when run from a checkout. Used only to find a default
# TypeScript compiler; an installed copy finds none there and says so.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))


def find_tool(name: str, candidates: Iterable[str] = ()) -> Optional[str]:
    """``name`` on PATH, else the first existing candidate path."""
    found = shutil.which(name)
    if found:
        return found
    for candidate in candidates:
        path = os.path.expanduser(candidate)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def cache_dir() -> str:
    """A per-user cache for built helpers (CUP_LINT_CACHE overrides)."""
    path = os.environ.get("CUP_LINT_CACHE") or os.path.join(tempfile.gettempdir(), "cup-lint-anonymous-steps")
    os.makedirs(path, exist_ok=True)
    return path


def digest(paths: Iterable[str]) -> str:
    sha = hashlib.sha256()
    for path in paths:
        with open(path, "rb") as handle:
            sha.update(handle.read())
    return sha.hexdigest()[:16]
