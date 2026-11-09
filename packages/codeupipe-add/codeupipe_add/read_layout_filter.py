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
            layout = json.loads(text, object_pairs_hook=lambda pairs: self._unique(path, pairs))
        except json.JSONDecodeError:
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
        unique = self._unique

        # A YAML reader keeps the last of two equal keys with no message; a layout refuses them.
        class UniqueKeyLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                pairs = [(self.construct_object(key, deep=deep), self.construct_object(value, deep=deep))
                         for key, value in node.value]
                return unique("%s, line %d" % (path, node.start_mark.line + 1), pairs)

        UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                        UniqueKeyLoader.construct_mapping)
        try:
            return yaml.load(text, Loader=UniqueKeyLoader)
        except yaml.YAMLError as error:
            raise Refusal(2, "The layout %s cannot be read: %s" % (path, error))

    def _unique(self, where, pairs):
        mapping = {}
        for key, value in pairs:
            if key in mapping:
                raise Refusal(2, "The layout %s has the key %s two times in one mapping. Keep one." % (where, key))
            mapping[key] = value
        return mapping
