"""BenchEachScenarioFilter: time each scenario, one after the other."""

import pathlib
import tempfile

from codeupipe import Payload

from .unsupported import ExportRefused


class BenchEachScenarioFilter:
    """Filter (sync).

    Input keys: ``cases`` (the scenarios), ``target``.
    Output keys: ``results``: for each scenario ``id``, ``us_per_run``,
    ``relative`` and ``output``, or ``{"id", "unsupported": reason}`` when
    the compiler refuses its pipeline.

    ``each`` is the pipeline that times one scenario.
    """

    def __init__(self, each):
        self.each = each

    def call(self, payload: Payload) -> Payload:
        target = payload.get("target")
        results = [self.one(case, target, index) for index, case in enumerate(payload.get("cases"))]
        return payload.insert("results", results)

    def one(self, case, target, index) -> dict:
        workdir = pathlib.Path(tempfile.mkdtemp(prefix="cup_bench_"))
        try:
            out = self.each.run(Payload({"case": case, "target": target, "workdir": workdir,
                                         "module_name": f"bench_predicates_{index}"}))
        except ExportRefused as reason:
            return {"id": case["id"], "unsupported": str(reason)}
        return {"id": case["id"], "us_per_run": out.get("us_per_run"), "relative": out.get("relative"),
                "output": out.get("output")}
