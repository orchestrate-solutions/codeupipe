"""Benchmark every target on the same scenarios, the same way.

    python conformance/bench.py                  # every target
    python conformance/bench.py python:run python:static-inline

Scenarios (bench/scenarios.json) use the conformance vocabulary, so every
runtime builds the same pipeline. Each runner times best of 5 x 20,000 runs
after 20,000 warmup runs (so JIT runtimes are measured warm) and reports the
output it produced; this script refuses a result whose output differs from
the others, so a fast wrong answer cannot win.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run as conformance  # noqa: E402  (same target definitions and launchers)

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"

BENCH_TARGETS = {
    "python:run": ("python:run", "bench:run"),
    "python:static-steps": ("python:static-steps", "bench:static-steps"),
    "python:static-inline": ("python:static-inline", "bench:static-inline"),
    "python:static-observe": ("python:static-observe", "bench:static-observe"),
}


def spec_for(target):
    base, mode = BENCH_TARGETS[target]
    spec = dict(conformance.TARGETS[base])
    cmd = list(spec["cmd"])
    cmd[-1] = mode
    spec["cmd"] = cmd
    return spec


def main(argv):
    scenarios = json.loads((HERE / "bench" / "scenarios.json").read_text())
    names = argv or list(BENCH_TARGETS)
    table, reference, problems, refused = {}, {}, [], []
    for name in names:
        results, error = conformance.run_target(name, spec_for(name), scenarios)
        if error:
            problems.append(f"{name}: {error}")
            continue
        table[name] = {}
        for sc in scenarios:
            r = results.get(sc["id"], {})
            if "unsupported" in r:
                # the target cannot express the scenario (e.g. fast static
                # export refuses Hooks): not a failure, and not a number
                refused.append(f"{name} {sc['id']}: {r['unsupported']}")
                continue
            if "us_per_run" not in r:
                problems.append(f"{name} {sc['id']}: {r.get('unsupported', 'no result')}")
                continue
            out = conformance._norm(r.get("output"))
            ref = reference.setdefault(sc["id"], (name, out))
            if out != ref[1]:
                problems.append(f"{name} {sc['id']}: output {r.get('output')!r} differs from {ref[0]}")
                continue
            table[name][sc["id"]] = r["us_per_run"]

    RESULTS.mkdir(exist_ok=True)
    report = {"scenarios": {s["id"]: {"about": s["about"], "steps": len(s["steps"])} for s in scenarios},
              "us_per_run": table, "problems": problems, "refused": refused}
    (RESULTS / "bench-latest.json").write_text(json.dumps(report, indent=2))
    md = markdown(scenarios, table, problems, refused)
    (RESULTS / "bench-latest.md").write_text(md)
    print(md)
    return 1 if problems else 0


def markdown(scenarios, table, problems, refused=()):
    targets = list(table)
    lines = ["µs per run (best of 5 × 20,000, after 20,000 warmup runs); lower is better.", "",
             "| scenario | steps | " + " | ".join(targets) + " |",
             "|---|---|" + "---|" * len(targets)]
    for sc in scenarios:
        row = [f"`{sc['id']}`", str(len(sc["steps"]))]
        for t in targets:
            v = table[t].get(sc["id"])
            row.append("—" if v is None else (f"{v:.2f}" if v >= 1 else f"{v:.3f}"))
        lines.append("| " + " | ".join(row) + " |")
    if refused:
        lines += ["", "Not measured (the target refuses the scenario):"] + [f"- {r}" for r in refused]
    if problems:
        lines += ["", "Problems:"] + [f"- {p}" for p in problems]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
