"""PlanFilesFilter: where the component file and the test file go."""

import pathlib

from codeupipe import Payload


class PlanFilesFilter:
    """Filter (sync).

    Input keys: ``directory`` (relative to the root), ``snake``.
    Output keys: ``component_path`` and ``test_path`` (relative to the root,
    with ``/``), and ``module`` (the import path of the component).
    """

    def call(self, payload: Payload) -> Payload:
        directory = pathlib.PurePosixPath(payload.get("directory") or ".")
        snake = payload.get("snake")
        component = (directory / (snake + ".py")).as_posix()
        parts = [part for part in directory.parts if part != "."] + [snake]
        return (payload.insert("component_path", component)
                .insert("test_path", "tests/test_%s.py" % snake)
                .insert("module", ".".join(parts)))
