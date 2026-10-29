"""WriteLayoutFilter: write each file of the layout that is not there yet."""

import pathlib

from codeupipe import Payload

from .refusal import Refusal


class WriteLayoutFilter:
    """Filter (sync).

    Input keys: ``root``, ``components`` (each with ``component_path``,
    ``component_text``, ``test_path``, ``test_text``).
    Output keys: ``written`` and ``kept``: the paths, in order, component
    first. A file that exists is kept, by itself. The directories are made
    before a file is written; one that cannot be made is refused with exit
    code 2.
    """

    def call(self, payload: Payload) -> Payload:
        root = pathlib.Path(payload.get("root"))
        files = [(component[path_key], component[text_key]) for component in payload.get("components")
                 for path_key, text_key in (("component_path", "component_text"), ("test_path", "test_text"))]
        kept = [path for path, _ in files if (root / path).exists()]
        new = [(path, text) for path, text in files if path not in kept]
        for path, _ in new:
            try:
                (root / path).parent.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise Refusal(2, "Cannot make the directory of %s: %s" % (path, error))
        for path, text in new:
            (root / path).write_text(text, encoding="utf-8")
        return payload.insert("written", [path for path, _ in new]).insert("kept", kept)
