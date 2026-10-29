"""RenderFilesFilter: the text of the component file and of the test file."""

from codeupipe import Payload

from .templates import COMPONENTS, TEST


class RenderFilesFilter:
    """Filter (sync).

    Input keys: ``kind``, ``type_name``, ``snake``, ``module``, ``description``.
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
        return (payload.insert("component_text", COMPONENTS[payload.get("kind")].format(**values))
                .insert("test_text", TEST.format(**values)))
