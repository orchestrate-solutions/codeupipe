"""Benchmark every target on the same scenarios, the same way.

    python conformance/bench.py                  # every target
    python conformance/bench.py python:run python:static-inline
    python conformance/bench.py --check          # compare with the recorded baseline
    python conformance/bench.py --record         # record a new baseline

Scenarios (bench/scenarios.json) use the conformance vocabulary, so every
runtime builds the same pipeline. Each runner times best of 5 x 20,000 runs
after 20,000 warmup runs (so JIT runtimes are measured warm) and reports the
output it produced; this script refuses a result whose output differs from
the others, so a fast wrong answer cannot win.

The comparison (--check) is for a machine whose resources are fixed, such as
a constrained container. CI does not run it: a shared machine is too noisy
to judge speed, so CI only measures and keeps the numbers.

A recorded time is true for one machine, so each
number is kept as a ratio to a reference workload: plain Python dict writes
and function calls, the work a pipeline does. The runner times the reference
and the scenario back to back, so a slower or a busier machine slows both
and the ratio stays. --check
fails when a ratio is more than --tolerance percent (default 25) away from
its baseline, in either direction: slower is a regression, and faster means
the baseline is out of date and must be recorded again, or the next
regression would hide inside the gain. A baseline is kept for each Python
version (bench/baseline.json), because interpreters differ in what they make
fast. The Rust run does not depend on Python, so it has one baseline, under
"rust". --record replaces only the targets that it measured.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run as conformance  # noqa: E402  (same target definitions and launchers)

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
BASELINE = HERE / "bench" / "baseline.json"
DEFAULT_TOLERANCE = 25.0

BENCH_TARGETS = {
    "python:run": ("python:run", "bench:run"),
    "python:static-steps": ("python:static-steps", "bench:static-steps"),
    "python:static-inline": ("python:static-inline", "bench:static-inline"),
    "python:static-observe": ("python:static-observe", "bench:static-observe"),
    "rust:run": ("rust:run", "bench:run"),
}


def spec_for(target):
    base, mode = BENCH_TARGETS[target]
    spec = dict(conformance.TARGETS[base])
    cmd = list(spec["cmd"])
    cmd[-1] = mode
    spec["cmd"] = cmd
    return spec


def python_key():
    return "%d.%d" % sys.version_info[:2]


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def load_baseline():
    return json.loads(BASELINE.read_text()) if BASELINE.exists() else {}


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def baseline_key(target, python):
    """Where the baseline of ``target`` is kept. A Python target is kept per
    Python version; the Rust run does not depend on Python and has its own."""
    return "rust" if target.startswith("rust:") else python


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def baseline_for(baseline, targets, python):
    """The recorded ratios of ``targets``, each from its own key."""
    relative = {}
    for target in targets:
        row = baseline.get(baseline_key(target, python), {}).get("relative", {}).get(target)
        if row is not None:
            relative[target] = row
    return {"relative": relative}


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def record_into(baseline, current, python):
    """Put the measured targets into ``baseline``. The others are kept."""
    for kind in ("relative", "us_per_run"):
        for target, row in current[kind].items():
            recorded = baseline.setdefault(baseline_key(target, python), {"relative": {}, "us_per_run": {}})
            recorded.setdefault(kind, {})[target] = row


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def compare(baseline, current, tolerance=DEFAULT_TOLERANCE):
    """Every number that is not within ``tolerance`` percent of its baseline.

    ``baseline`` and ``current`` are {"relative": {target: {scenario: ratio}}},
    each ratio a scenario's time over the reference workload's. Returns [{"target", "scenario", "kind", "change_percent"}],
    kind one of slower, faster, missing, not recorded.
    """
    problems = []
    was, now = baseline["relative"], current["relative"]
    for target in sorted(set(was) | set(now)):
        for scenario in sorted(set(was.get(target, {})) | set(now.get(target, {}))):
            before, after = was.get(target, {}).get(scenario), now.get(target, {}).get(scenario)
            if before is None or after is None:
                problems.append({"target": target, "scenario": scenario, "change_percent": None,
                                 "kind": "not recorded" if before is None else "missing"})
                continue
            change = (after / before - 1) * 100
            if abs(change) > tolerance:
                problems.append({"target": target, "scenario": scenario, "change_percent": change,
                                 "kind": "slower" if change > 0 else "faster"})
    return problems


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def _report(problems, tolerance):
    if not problems:
        return "Speed check: every number is within %g%% of its baseline." % tolerance
    lines = ["Speed check: %d number(s) outside %g%% of the baseline." % (len(problems), tolerance)]
    for p in problems:
        where = "%s %s" % (p["target"], p["scenario"])
        if p["kind"] == "slower":
            lines.append("- %s: %+.0f%% slower. A regression: find the change that caused it." % (where, p["change_percent"]))
        elif p["kind"] == "faster":
            lines.append("- %s: %+.0f%% (faster). Record the gain: python conformance/bench.py --record" % (where, p["change_percent"]))
        elif p["kind"] == "missing":
            lines.append("- %s: in the baseline, not measured now." % where)
        else:
            lines.append("- %s: measured now, not in the baseline. Record it: python conformance/bench.py --record" % where)
    return "\n".join(lines)


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
def main(argv):
    argv = list(argv)
    record, check = "--record" in argv, "--check" in argv
    tolerance = DEFAULT_TOLERANCE
    if "--tolerance" in argv:
        at = argv.index("--tolerance")
        tolerance = float(argv[at + 1])
        del argv[at:at + 2]
    argv = [a for a in argv if a not in ("--record", "--check")]

    scenarios = json.loads((HERE / "bench" / "scenarios.json").read_text())
    runnable = conformance.default_targets()
    names = argv or [name for name in BENCH_TARGETS if BENCH_TARGETS[name][0] in runnable]
    table, relative, reference, problems, refused = {}, {}, {}, [], []
    for name in names:
        results, error = conformance.run_target(name, spec_for(name), scenarios)
        if error:
            problems.append(f"{name}: {error}")
            continue
        table[name], relative[name] = {}, {}
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
            relative[name][sc["id"]] = r["relative"]
    current = {"relative": relative, "us_per_run": table}

    RESULTS.mkdir(exist_ok=True)
    report = {"scenarios": {s["id"]: {"about": s["about"], "steps": len(s["steps"])} for s in scenarios},
              "relative": relative, "us_per_run": table, "problems": problems, "refused": refused}
    (RESULTS / "bench-latest.json").write_text(json.dumps(report, indent=2))
    md = markdown(scenarios, table, problems, refused)
    (RESULTS / "bench-latest.md").write_text(md)
    print(md)
    if problems:
        return 1

    if record:
        baseline = load_baseline()
        record_into(baseline, current, python_key())
        BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
        print("Recorded the baseline of %s in %s." % (", ".join(names), BASELINE.relative_to(HERE.parent)))
        return 0
    if check:
        baseline = load_baseline()
        if python_key() not in baseline and any(name.startswith("python:") for name in names):
            print("Speed check: no baseline for Python %s. Record one: python conformance/bench.py --record"
                  % python_key())
            return 1
        found = compare(baseline_for(baseline, names, python_key()), current, tolerance)
        print(_report(found, tolerance))
        return 1 if found else 0
    return 0


# cup: allow-plain the speed check of the conformance suite: it times the scenarios and compares them with the baseline
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
