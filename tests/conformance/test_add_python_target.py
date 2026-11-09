"""The Python ``codeupipe add`` must pass every case of conformance/add/."""

import json
import pathlib
import sys

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

import add as conformance_add  # noqa: E402
from judging.add_launcher import AddLauncher  # noqa: E402
from judging.judge_add_filter import JudgeAddFilter  # noqa: E402
from judging.load_cases_filter import LoadCasesFilter  # noqa: E402


def test_python_passes_every_case():
    cases = LoadCasesFilter().load(conformance_add.CASES)
    results, error = AddLauncher(conformance_add.REPO).run(conformance_add.targets()["python:add"], cases)
    assert error is None, error
    verdicts = {case["id"]: JudgeAddFilter().judge(case, results.get(case["id"])) for case in cases}
    not_passed = {case_id: verdict for case_id, verdict in verdicts.items() if verdict[0] != "pass"}
    assert not_passed == {}, json.dumps(not_passed, indent=2)
