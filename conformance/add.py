"""Run the cases of ``codeupipe add`` against every target and judge them one way.

    python conformance/add.py                 # all targets
    python conformance/add.py python:add

The contract is conformance/ADD.md, and the cases are in conformance/add/.
Each target is a file in conformance/add/targets/: how to run the command,
what a new project of the language has, the linter, and the test. With no
arguments, a TypeScript target runs only when the machine has Node 22.18 or
later, a Rust target only when it has cargo, and a Go target only when it has
go. A target that is named and cannot run is a failure.

The judge makes a new project for each case, runs the command in it, and then
the linter and the test on the files that the command made.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
CASES = HERE / "add"
RESULTS = HERE / "results" / "add"
sys.path.insert(0, str(HERE))

from codeupipe import Payload  # noqa: E402

from judging.add_judge_pipeline import AddJudgePipeline  # noqa: E402
from judging.add_launcher import AddLauncher  # noqa: E402
from judging.cargo_probe import CargoProbe  # noqa: E402
from judging.go_probe import GoProbe  # noqa: E402
from judging.node_probe import NodeProbe  # noqa: E402


def targets():
    """Each target, from its file: ``python.json`` gives ``python:add``."""
    return {"%s:add" % path.stem: json.loads(path.read_text())
            for path in sorted((CASES / "targets").glob("*.json"))}


def main(argv):
    pipeline = AddJudgePipeline(AddLauncher(REPO), lambda: NodeProbe().runs_typescript(),
                                lambda: CargoProbe().present(), lambda: GoProbe().present())
    out = pipeline.run(Payload({"cases_dir": CASES, "results_dir": RESULTS, "targets": targets(),
                                "needs": {}, "names": list(argv)}))
    print(out.get("markdown"))
    return out.get("exit_code")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
