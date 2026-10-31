"""WriteFilesFilter: write the two files, and the directories that they need."""

import pathlib

from codeupipe import Payload

from .refusal import Refusal


class WriteFilesFilter:
    """Filter (sync).

    Input keys: ``root``, ``component_path``, ``component_text``,
    ``test_path``, ``test_text``.
    Output keys: ``written`` (the two paths, component first). A directory
    that cannot be made is refused with exit code 2, before a file is written.
    """

    def call(self, payload: Payload) -> Payload:
        root = pathlib.Path(payload.get("root"))
        files = [(payload.get("component_path"), payload.get("component_text")),
                 (payload.get("test_path"), payload.get("test_text"))]
        for path, _ in files:
            try:
                (root / path).parent.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise Refusal(2, "Cannot make the directory of %s: %s" % (path, error))
        for path, text in files:
            (root / path).write_text(text, encoding="utf-8")
        return payload.insert("written", [path for path, _ in files])
