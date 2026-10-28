"""LoadCasesFilter: read the conformance cases from disk."""

import json
import pathlib

from codeupipe import Payload


class LoadCasesFilter:
    """Filter (sync).

    Input keys: ``cases_dir`` (the directory of the ``*.json`` case files).
    Output keys: ``cases`` (each case, in the order of the file names). Two
    cases with the same id stop the run.
    """

    def call(self, payload: Payload) -> Payload:
        return payload.insert("cases", self.load(payload.get("cases_dir")))

    def load(self, cases_dir) -> list:
        cases = []
        for path in sorted(pathlib.Path(cases_dir).glob("*.json")):
            cases.extend(json.loads(path.read_text()))
        ids = [case["id"] for case in cases]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise SystemExit(f"duplicate case ids: {sorted(duplicates)}")
        return cases
