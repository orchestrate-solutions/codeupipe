"""RenderFilesFilter: the text of the component file and of the test file."""

from codeupipe import Payload

from .templates import COMPONENTS, PIPELINE_STEPS, TEST


class RenderFilesFilter:
    """Filter (sync).

    Input keys: ``kind``, ``type_name``, ``snake``, ``module``, ``description``;
    for a pipeline of a layout, also ``calls`` and ``imports``
    (ResolveStepsFilter).
    Output keys: ``component_text``, ``test_text``. With no description, the
    header says ``TODO: say what <type_name> does.``
    """

    def call(self, payload: Payload) -> Payload:
        type_name = payload.get("type_name")
        description = payload.get("description") or "TODO: say what %s does." % type_name
        # The description goes inside a docstring: a backslash or three quotes would end it early.
        description = description.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        values = {"type_name": type_name, "description": description,
                  "module": payload.get("module"), "snake": payload.get("snake")}
        calls = payload.get("calls") or []
        if calls:
            values["imports"] = "\n".join("from %s import %s" % pair for pair in payload.get("imports"))
            values["calls"] = "\n".join("        self.%s(%s)" % (method, ", ".join(name + "()" for name in names))
                                        for method, names in calls)
            component = PIPELINE_STEPS.format(**values)
        else:
            component = COMPONENTS[payload.get("kind")].format(**values)
        return payload.insert("component_text", component).insert("test_text", TEST.format(**values))
