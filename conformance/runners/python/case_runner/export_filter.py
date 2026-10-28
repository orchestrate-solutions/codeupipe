"""ExportFilter: compile the pipeline of the case and import the package from disk, as a customer would."""

import importlib
import sys

from codeupipe import Payload

from .unsupported import ExportRefused


class ExportFilter:
    """Filter (sync).

    Input keys: ``pipeline``, ``lowering``, ``observe``, ``workdir``.
    Output keys: ``package``: the compiled code, with its ``run`` function.

    The compiler refuses a pipeline that it cannot keep equal. For the fast
    forms that is an ExportRefused: the target cannot express the case. With
    ``observe`` the error is given as it is.
    """

    def call(self, payload: Payload) -> Payload:
        try:
            package = self.load(payload.get("pipeline"), payload.get("lowering"), payload.get("observe"),
                                payload.get("workdir"))
        except Exception as error:  # noqa: BLE001 — the compiler refused the shape (for example Hooks)
            if payload.get("observe"):
                raise
            raise ExportRefused(f"{type(error).__name__}: {error}") from error
        return payload.insert("package", package)

    def load(self, pipeline, lowering, observe, workdir):
        from codeupipe.compile import build_export_pipeline_v2

        out = build_export_pipeline_v2(write=False).run(
            Payload({"pipeline": pipeline, "pattern": "flat", "lowering": lowering, "observe": observe}))
        for file in out.get("files") or []:
            target = workdir / file["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file["content"])
        package_parent = str(workdir / "src")
        for name in [m for m in sys.modules if m == "steps" or m.startswith("steps.")]:
            del sys.modules[name]
        sys.path.insert(0, package_parent)
        try:
            return importlib.import_module("steps")
        finally:
            sys.path.remove(package_parent)
