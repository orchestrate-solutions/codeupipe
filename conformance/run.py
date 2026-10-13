"""Run the conformance cases against every target and judge them one way.

    python conformance/run.py                 # all targets
    python conformance/run.py python:run python:static-inline
    python conformance/run.py typescript:run

With no arguments, the TypeScript target runs only when the machine has
Node 22.18 or later. A target that is named and cannot run is a failure.

A runner executes cases and reports what happened. Only this file decides
pass or fail, so every target is held to exactly the same comparison.

Result per case and target:
    pass         every expectation matched
    partial      every expectation the target can observe matched, but some
                 (State, Hooks) it does not expose at all (fast static code)
    FAIL         something observable differed (details in the JSON report)
    unsupported  the target cannot express the case (e.g. compiled form of a
                 nested pipeline); reported, never counted as a pass
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
CASES = HERE / "cases"
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

from codeupipe import Payload  # noqa: E402

from judging.default_targets_filter import DefaultTargetsFilter  # noqa: E402
from judging.judge_pipeline import JudgePipeline  # noqa: E402
from judging.judge_results_filter import JudgeResultsFilter  # noqa: E402
from judging.load_cases_filter import LoadCasesFilter  # noqa: E402
from judging.node_probe import NodeProbe  # noqa: E402
from judging.process_launcher import ProcessLauncher  # noqa: E402

PYTHON = sys.executable


def _python(target):
    return {
        "cmd": [PYTHON, str(HERE / "runners/python/runner.py"), target],
        "env": {"PYTHONPATH": str(REPO)},
        "cwd": REPO,
    }


def _typescript(target):
    # Node runs the .ts file as it is. Nothing is built or downloaded.
    return {
        "cmd": ["node", str(HERE / "runners/typescript/runner.ts"), target],
        "env": {},
        "cwd": REPO,
    }


TARGETS = {
    "python:run": _python("run"),
    "python:run_async": _python("run_async"),
    "python:static-steps": _python("static-steps"),
    "python:static-inline": _python("static-inline"),
    "python:static-observe": _python("static-observe"),
    "typescript:run": _typescript("run"),
    "typescript:static": _typescript("static"),
}

# The static target runs the compile package. Its dependencies must be
# installed (npm ci at the repository root), and it uses the built core
# package.
_TYPESCRIPT_NEEDS = {
    "typescript:static": [REPO / "node_modules/typescript",
                          REPO / "packages/codeupipe-ts/dist/index.js"],
}


# The judge is the pipeline in judging/. The functions below give its parts to the tests and to bench.py
# under the names that they had. Each one calls a step of the pipeline, so there is one judge.

def _node_runs_typescript():
    """Whether there is a Node that runs a .ts file as it is (22.18 or later)."""
    return NodeProbe().runs_typescript()


def default_targets():
    """Every target that this machine can run. TypeScript needs Node, and the
    static TypeScript target needs its package to be installed."""
    return DefaultTargetsFilter(lambda: _node_runs_typescript()).choose(TARGETS, _TYPESCRIPT_NEEDS)


def load_cases():
    return LoadCasesFilter().load(CASES)


def run_target(name, spec, cases):
    return ProcessLauncher().run(spec, cases)


def _norm(value):
    """JSON equality: 1 == 1.0, but true is not 1."""
    return JudgeResultsFilter().norm(value)


def judge(case, result):
    """Return (status, problems)."""
    return JudgeResultsFilter().judge(case, result)


def main(argv):
    pipeline = JudgePipeline(ProcessLauncher(), lambda: _node_runs_typescript())
    out = pipeline.run(Payload({"cases_dir": CASES, "results_dir": RESULTS, "targets": TARGETS,
                                "needs": _TYPESCRIPT_NEEDS, "names": list(argv)}))
    print(out.get("markdown"))
    return out.get("exit_code")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
