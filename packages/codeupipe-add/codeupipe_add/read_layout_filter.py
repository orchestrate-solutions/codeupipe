"""ReadLayoutFilter: the layout file, as data."""

import json
import pathlib

from codeupipe import Payload

from .refusal import Refusal


class ReadLayoutFilter:
    """Filter (sync).

    Input keys: ``root``, ``layout_path`` (relative to the root).
    Output keys: ``layout`` (a dict). JSON is read with the standard library;
    YAML needs PyYAML (``codeupipe-add[layout]``). A file that cannot be read,
    or that is not a mapping, is refused with exit code 2.
    """

    def call(self, payload: Payload) -> Payload:
        path = payload.get("layout_path")
        try:
            text = (pathlib.Path(payload.get("root")) / path).read_text(encoding="utf-8")
        except OSError as error:
            raise Refusal(2, "The layout %s cannot be read: %s" % (path, error.strerror or error))
        try:
            layout = json.loads(text)
        except ValueError:
            layout = self._yaml(path, text)
        if not isinstance(layout, dict):
            raise Refusal(2, "The layout %s is not a mapping. It starts with keys such as lang: and components:."
                          % path)
        return payload.insert("layout", layout)

    def _yaml(self, path, text):
        try:
            import yaml
        except ImportError:
            raise Refusal(2, "The layout %s is YAML, and reading YAML needs PyYAML: "
                             "pip install 'codeupipe-add[layout]'. A layout in JSON needs nothing." % path)
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise Refusal(2, "The layout %s cannot be read: %s" % (path, error))
