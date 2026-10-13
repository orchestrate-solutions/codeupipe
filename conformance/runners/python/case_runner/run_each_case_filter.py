"""RunEachCaseFilter: play each case, one after the other, each in its own directory."""

import pathlib
import tempfile

import conformance_sink as sink
from codeupipe import Payload

from .unsupported import Unsupported


class RunEachCaseFilter:
    """Filter (sync).

    Input keys: ``cases``, ``target``.
    Output keys: ``results``: for each case its result, or ``{"id",
    "unsupported": reason}`` when the target cannot express it.

    ``each`` is the pipeline that plays one case.
    """

    def __init__(self, each):
        self.each = each

    def call(self, payload: Payload) -> Payload:
        target = payload.get("target")
        results = [self.one(case, target, index) for index, case in enumerate(payload.get("cases"))]
        return payload.insert("results", results)

    def one(self, case, target, index) -> dict:
        sink.reset()
        workdir = pathlib.Path(tempfile.mkdtemp(prefix="cup_conf_"))
        try:
            out = self.each.run(Payload({"case": case, "target": target, "workdir": workdir,
                                         "module_name": f"conf_predicates_{index}"}))
        except Unsupported as reason:
            return {"id": case["id"], "unsupported": str(reason)}
        except Exception as error:  # noqa: BLE001 — for example the compiler refuses a shape
            return {"id": case["id"], "unsupported": f"{type(error).__name__}: {error}"}
        return out.get("result")
