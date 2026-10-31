"""CheckLayoutFilter: the keys of the layout, and the shape of each."""

from codeupipe import Payload

from .refusal import Refusal

LANG = "python"
LAYOUT_KEYS = ("lang", "root", "components")
COMPONENT_KEYS = ("kind", "name", "description", "steps", "hooks")


class CheckLayoutFilter:
    """Filter (sync).

    Input keys: ``layout``.
    Output keys: ``directory`` (``root``, or ``.``), and ``components``: a
    list of dicts, each with every key of COMPONENT_KEYS. A layout with a key
    that is not known, a key that is missing, or a value of the wrong shape is
    refused with exit code 2. The names are checked by the next steps.
    """

    def call(self, payload: Payload) -> Payload:
        layout = payload.get("layout")
        self._known(layout, LAYOUT_KEYS, "the layout")
        if "lang" not in layout:
            raise Refusal(2, "The layout has no lang:. For this command it is lang: %s." % LANG)
        if layout["lang"] != LANG:
            raise Refusal(2, "The layout is for %s, and this is codeupipe add for %s." % (layout["lang"], LANG))
        root = layout.get("root", ".")
        if not isinstance(root, str) or not root:
            raise Refusal(2, "root: is a directory, such as src/pricing.")
        listed = layout.get("components")
        if not isinstance(listed, list) or not listed:
            raise Refusal(2, "components: is a list with one component or more, each with kind: and name:.")
        return payload.insert("directory", root).insert("components", [self._component(item) for item in listed])

    def _component(self, item):
        if not isinstance(item, dict):
            raise Refusal(2, "A component is a mapping with kind: and name:, not %r." % (item,))
        label = "the component %s" % item.get("name", "with no name")
        self._known(item, COMPONENT_KEYS, label)
        for key in ("kind", "name"):
            if not isinstance(item.get(key), str):
                raise Refusal(2, "%s has no %s:." % (label[0].upper() + label[1:], key))
        description = item.get("description", "")
        if not isinstance(description, str):
            raise Refusal(2, "The description of %s is not a text." % label)
        for key in ("steps", "hooks"):
            if key in item and item["kind"] != "pipeline":
                raise Refusal(2, "%s: is only for a pipeline, and %s is a %s." % (key, item["name"], item["kind"]))
        steps, hooks = item.get("steps", []), item.get("hooks", [])
        if not isinstance(steps, list):
            raise Refusal(2, "The steps of %s are a list. A step is a name, or valve: [Predicate, Filter]."
                          % item["name"])
        for step in steps:
            if not self._step(step):
                raise Refusal(2, "The step %r of %s cannot be read. A step is a name, or valve: [Predicate, Filter]."
                              % (step, item["name"]))
        if not isinstance(hooks, list) or not all(isinstance(hook, str) for hook in hooks):
            raise Refusal(2, "The hooks of %s are a list of names." % item["name"])
        return {"kind": item["kind"], "name": item["name"], "description": description,
                "steps": steps, "hooks": hooks}

    def _step(self, step):
        if isinstance(step, str):
            return True
        return (isinstance(step, dict) and list(step) == ["valve"] and isinstance(step["valve"], list)
                and len(step["valve"]) == 2 and all(isinstance(name, str) for name in step["valve"]))

    def _known(self, mapping, keys, label):
        unknown = [key for key in mapping if key not in keys]
        if unknown:
            raise Refusal(2, "Unknown key %s in %s. The keys are: %s."
                          % (", ".join(map(str, unknown)), label, ", ".join(keys)))
