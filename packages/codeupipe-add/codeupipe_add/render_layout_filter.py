"""RenderLayoutFilter: the text of the two files of each component of the layout."""

from codeupipe import Payload

from .render_files_filter import RenderFilesFilter


class RenderLayoutFilter:
    """Filter (sync).

    Input keys: ``components`` (ResolveStepsFilter).
    Output keys: ``components``, each with ``component_text`` and
    ``test_text``, from the RenderFilesFilter of phase 1.
    """

    def call(self, payload: Payload) -> Payload:
        rendered = []
        for component in payload.get("components"):
            out = RenderFilesFilter().call(Payload(component))
            rendered.append(dict(component, component_text=out.get("component_text"), test_text=out.get("test_text")))
        return payload.insert("components", rendered)
