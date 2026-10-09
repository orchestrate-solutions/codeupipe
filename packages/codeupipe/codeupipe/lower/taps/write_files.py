"""
WriteFilesTap — side-effect: write the emitter's ``files`` list to disk.

Direction: both.
Milestone: M1.
"""

from __future__ import annotations

from pathlib import Path

from codeupipe.core import Payload


__all__ = ["WriteFilesTap"]


class WriteFilesTap:
    """Observe the ``files`` payload key and write each entry to disk."""

    def observe(self, payload: Payload) -> None:
        files = payload.get("files") or []
        output_dir = payload.get("output_dir")
        dry_run = bool(payload.get("dry_run", False))

        if not files:
            return
        if not output_dir:
            return
        if dry_run:
            return

        root = Path(output_dir)
        for file_info in files:
            path = root / file_info["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(file_info["content"], encoding="utf-8")
