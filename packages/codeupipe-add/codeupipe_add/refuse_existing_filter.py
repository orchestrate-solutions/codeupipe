"""RefuseExistingFilter: a file that exists is never written over."""

import pathlib

from codeupipe import Payload

from .refusal import Refusal


class RefuseExistingFilter:
    """Filter (sync).

    Input keys: ``root``, ``component_path``, ``test_path``.
    Output keys: none. When either file exists, it refuses with exit code 1,
    and names each file that exists. Both files are checked before one is
    written, so the command writes both or neither.
    """

    def call(self, payload: Payload) -> Payload:
        root = pathlib.Path(payload.get("root"))
        there = [path for path in (payload.get("component_path"), payload.get("test_path")) if (root / path).exists()]
        if there:
            raise Refusal(1, "\n".join("%s exists" % path for path in there))
        return payload
