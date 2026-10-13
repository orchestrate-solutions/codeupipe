"""Python conformance runner: executes cases, reports what happened.

    python runner.py <target> < cases.json > results.json

Targets
    run            codeupipe Pipeline.run (sync, the default)
    run_async      codeupipe Pipeline.run_async (inside asyncio.run)
    static-steps   codeupipe.compile export, per-step layout, loaded from disk
    static-inline  codeupipe.compile export, lowering="inline", loaded from disk
    static-observe codeupipe.compile export, observe=True: State and Hooks too

With ``bench:<target>`` it times the scenarios that it gets, and does not
play cases (conformance/bench.py).

The runner is two codeupipe pipelines, in ``case_runner/``: one plays a
case, and one times a scenario. This file is its command line.

The runner never judges; conformance/run.py compares every target's results
against the same expectations. The fast static targets have no State or
Hooks, so they omit those fields and the orchestrator skips those checks;
static-observe reports both and is judged on them.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from codeupipe import Payload  # noqa: E402

from case_runner.bench_each_scenario_filter import BenchEachScenarioFilter  # noqa: E402
from case_runner.bench_scenario_pipeline import BenchScenarioPipeline  # noqa: E402
from case_runner.run_case_pipeline import RunCasePipeline  # noqa: E402
from case_runner.run_each_case_filter import RunEachCaseFilter  # noqa: E402
from case_runner.runner_pipeline import RunnerPipeline  # noqa: E402

# Is the first argument "bench:<target>"? Then the runner times scenarios. If not, it plays cases.
_PIPELINES = {
    False: lambda: RunnerPipeline(RunEachCaseFilter(RunCasePipeline())),
    True: lambda: RunnerPipeline(BenchEachScenarioFilter(BenchScenarioPipeline())),
}


def main():
    target = sys.argv[1]
    pipeline = _PIPELINES[target.startswith("bench:")]()
    out = pipeline.run(Payload({"cases": json.load(sys.stdin), "target": target.removeprefix("bench:")}))
    json.dump(out.get("results"), sys.stdout)


if __name__ == "__main__":
    main()
