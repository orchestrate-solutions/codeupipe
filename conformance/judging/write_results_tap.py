"""WriteResultsTap: put the report and the matrix on disk."""

import json
import pathlib

from codeupipe import Payload


class WriteResultsTap:
    """Tap (sync).

    Reads ``results_dir``, ``report`` and ``markdown``, and writes
    ``latest.json`` and ``latest.md`` in that directory.
    """

    def observe(self, payload: Payload) -> None:
        directory = pathlib.Path(payload.get("results_dir"))
        directory.mkdir(exist_ok=True)
        (directory / "latest.json").write_text(json.dumps(payload.get("report"), indent=2))
        (directory / "latest.md").write_text(payload.get("markdown"))
