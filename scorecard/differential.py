"""Item 1 + 4: random-pipeline differential testing, with isolation checks.

    python -m scorecard.differential --seed 20260927 --count 2000

For every generated case: run dynamic, fast steps, fast inline and
observable export. A mode passes when it agrees with dynamic on
output-or-error, Tap records and an unchanged caller input (observe also: State,
the full Hook event sequence with payload snapshots, and timing keys), and
its own run is isolated (no payload changed after a Hook saw it, a rerun is
identical). A mode that refuses with UnsupportedFilterShape is counted as
*refused*: not a pass. Anything else is a fail, and the case is shrunk to a
minimal reproducer.

Writes scorecard/results/differential-<seed>-<count>.json and .md.
"""

import argparse
import collections
import json
import pathlib
import time

from scorecard import case_gen, vocab
from scorecard.compare import divergences, self_checks, verdict
from scorecard.minimize import minimize
from scorecard.modes import run_dynamic, run_fast, run_observe

__all__ = ["check_case", "run_campaign", "main", "MODES"]

MODES = ("steps", "inline", "observe")
RESULTS = pathlib.Path(__file__).resolve().parent / "results"


def check_case(case):
    """{"dynamic": [self-check failures], "modes": {mode: {verdict, divergences, reason}}}"""
    predicates = vocab.make_predicates(case["steps"], vocab.new_workdir())
    dynamic = run_dynamic(case, predicates)
    result = {"dynamic": self_checks(dynamic, "dynamic"), "modes": {}}
    for mode in MODES:
        record = run_observe(case, predicates) if mode == "observe" else run_fast(case, predicates, mode)
        found = divergences(dynamic, record, mode)
        result["modes"][mode] = {"verdict": verdict(record, found), "divergences": found,
                                 "reason": record.get("reason")}
    return result


def failure_signature(result):
    """What a reproducer must keep failing on: (mode, check) pairs."""
    sig = {("dynamic", d["check"]) for d in result["dynamic"]}
    for mode, r in result["modes"].items():
        sig |= {(mode, d["check"]) for d in r["divergences"]}
    return sig


def _refusal_kind(reason):
    """'<node kind>' from 'name.call at line 0:0 — cannot lower <kind>. Hint: ...'"""
    if reason and "cannot lower " in reason:
        return reason.split("cannot lower ", 1)[1].split(".", 1)[0]
    return reason or "?"


def run_campaign(seed, count, hostile_rate=0.15, max_repros=12, max_steps=8, max_depth=2):
    started = time.time()
    cases = case_gen.generate_cases(seed, count, max_steps=max_steps, max_depth=max_depth,
                                    hostile_rate=hostile_rate)
    tally = {mode: collections.Counter() for mode in MODES}
    refusals = {mode: collections.Counter() for mode in MODES}
    checks = collections.Counter()
    isolation = collections.Counter()
    dynamic_failures = []
    failures = []
    for case in cases:
        result = check_case(case)
        if result["dynamic"]:
            dynamic_failures.append({"case": case, "problems": result["dynamic"]})
        for d in result["dynamic"]:
            isolation["dynamic:" + d["check"]] += 1
        failed = False
        for mode, r in result["modes"].items():
            tally[mode][r["verdict"]] += 1
            if r["verdict"] == "refused":
                refusals[mode][_refusal_kind(r["reason"])] += 1
            for d in r["divergences"]:
                checks[f"{mode}:{d['check']}"] += 1
                if d["check"] in ("input_mutated", "rerun_differs"):
                    isolation[f"{mode}:{d['check']}"] += 1
            failed = failed or r["verdict"] == "fail"
        if failed or result["dynamic"]:
            failures.append({"case": case, "result": result})

    # one minimized reproducer per distinct failure signature
    repros, seen = [], set()
    for failure in failures:
        sig = frozenset(failure_signature(failure["result"]))
        if sig in seen or len(repros) >= max_repros:
            continue
        seen.add(sig)
        small = minimize(failure["case"], lambda c, s=sig: s <= failure_signature(check_case(c)))
        repros.append({"signature": sorted(map(list, sig)), "original_id": failure["case"]["id"],
                       "minimal_case": small, "result": check_case(small)})

    hooked = sum(1 for c in cases if c["hooks"])
    hostile = sum(1 for c in cases if c["hostile_names"])
    nested = sum(1 for c in cases if any(s["kind"] == "pipeline" for s in vocab.walk_steps(c["steps"])))
    return {
        "seed": seed, "count": count, "hostile_rate": hostile_rate,
        "max_steps": max_steps, "max_depth": max_depth,
        "seconds": round(time.time() - started, 1),
        "corpus": {"cases": count, "with_hooks": hooked, "with_hostile_names": hostile,
                   "with_nested_pipelines": nested,
                   "steps_total": sum(len(list(vocab.walk_steps(c["steps"]))) for c in cases)},
        "verdicts": {mode: dict(tally[mode]) for mode in MODES},
        "refusals_by_kind": {mode: dict(refusals[mode]) for mode in MODES},
        "divergences_by_check": dict(checks),
        "isolation_violations": dict(isolation),
        "failing_cases": len(failures),
        "failing_cases_hostile_names": sum(1 for f in failures if f["case"]["hostile_names"]),
        "dynamic_self_check_failures": dynamic_failures[:5],
        "reproducers": repros,
    }


def markdown(report):
    lines = [f"# Differential run: seed {report['seed']}, {report['count']} cases",
             "", f"{report['seconds']} s. Corpus: " + ", ".join(f"{k} {v}" for k, v in report["corpus"].items()) + ".",
             "", "| mode | pass | refused | fail |", "|---|---|---|---|"]
    for mode in MODES:
        v = report["verdicts"][mode]
        lines.append(f"| {mode} | {v.get('pass', 0)} | {v.get('refused', 0)} | {v.get('fail', 0)} |")
    lines += ["", f"Failing cases: {report['failing_cases']} "
              f"(of which with hostile step names: {report['failing_cases_hostile_names']}).",
              "", "Isolation violations (input mutated, rerun differs): "
              + (json.dumps(report["isolation_violations"]) if report["isolation_violations"] else "**none**") + "."]
    if report["divergences_by_check"]:
        lines += ["", "Divergences by check:", ""]
        lines += [f"- `{k}`: {v}" for k, v in sorted(report["divergences_by_check"].items())]
    for mode in MODES:
        if report["refusals_by_kind"][mode]:
            lines += ["", f"Refusals ({mode}), by what was refused: "
                      + ", ".join(f"`{k}` {v}" for k, v in report["refusals_by_kind"][mode].items())]
    if report["reproducers"]:
        lines += ["", "## Minimized reproducers", ""]
        for r in report["reproducers"]:
            lines += [f"### {', '.join('/'.join(s) for s in r['signature'])}", "",
                      "```json", json.dumps(r["minimal_case"], ensure_ascii=False), "```", ""]
            for mode, m in r["result"]["modes"].items():
                for d in m["divergences"]:
                    lines.append(f"- {mode} `{d['check']}`: {d['detail'][:300]}")
            for d in r["result"]["dynamic"]:
                lines.append(f"- dynamic `{d['check']}`: {d['detail'][:300]}")
            lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--hostile-rate", type=float, default=0.15,
                        help="share of cases whose step names come from the hostile pool")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-repros", type=int, default=12,
                        help="minimize at most this many distinct failure signatures")
    parser.add_argument("--out", default=None, help="results file stem (default differential-<seed>-<count>)")
    args = parser.parse_args(argv)
    report = run_campaign(args.seed, args.count, args.hostile_rate, max_repros=args.max_repros,
                          max_steps=args.max_steps,
                          max_depth=args.max_depth)
    RESULTS.mkdir(exist_ok=True)
    stem = args.out or f"differential-{args.seed}-{args.count}"
    (RESULTS / f"{stem}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    md = markdown(report)
    (RESULTS / f"{stem}.md").write_text(md)
    print(md)
    return 1 if report["failing_cases"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
