"""StalePipelinesFilter: a kept pipeline file whose steps are not those of the layout."""

import pathlib
import re

from codeupipe import Payload

CALL = re.compile(r"self\.(add_filter|add_valve|add_tap|add_pipeline|use_hook)\(")
TYPE = re.compile(r"\b([A-Z]\w*)\(")
COMMENT = re.compile(r"#[^\n]*")


class StalePipelinesFilter:
    """Filter (sync).

    Input keys: ``root``, ``components``, ``kept``.
    Output keys: ``stale``: the path of each kept pipeline file whose steps
    (the method and the types of each call, in order) are not those that the
    layout gives. The arguments of a step and the comments do not count, so
    a file that a user filled in is not stale while its steps are the same.
    """

    def call(self, payload: Payload) -> Payload:
        root, kept = pathlib.Path(payload.get("root")), set(payload.get("kept"))
        stale = [component["component_path"] for component in payload.get("components")
                 if component["kind"] == "pipeline" and component["component_path"] in kept
                 and self._steps((root / component["component_path"]).read_text(encoding="utf-8"))
                 != self._steps(component["component_text"])]
        return payload.insert("stale", stale)

    def _steps(self, text):
        text = COMMENT.sub("", text)
        steps = []
        for found in CALL.finditer(text):
            depth, end = 1, found.end()
            while depth and end < len(text):
                depth += {"(": 1, ")": -1}.get(text[end], 0)
                end += 1
            steps.append((found.group(1), TYPE.findall(text[found.end():end])))
        return steps
