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

import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
CASES = HERE / "cases"
RESULTS = HERE / "results"

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


def _node_runs_typescript():
    """Whether there is a Node that runs a .ts file as it is (22.18 or later)."""
    node = shutil.which("node")
    if node is None:
        return False
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout
        major, minor = (int(part) for part in version.strip().lstrip("v").split(".")[:2])
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return (major, minor) >= (22, 18)


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


def default_targets():
    """Every target that this machine can run. TypeScript needs Node, and the
    static TypeScript target needs its package to be installed."""
    def can_run(name):
        if not name.startswith("typescript:"):
            return True
        return _node_runs_typescript() and all(path.exists() for path in _TYPESCRIPT_NEEDS.get(name, []))
    return [name for name in TARGETS if can_run(name)]


def load_cases():
    cases = []
    for path in sorted(CASES.glob("*.json")):
        cases.extend(json.loads(path.read_text()))
    ids = [c["id"] for c in cases]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise SystemExit(f"duplicate case ids: {sorted(duplicates)}")
    return cases


def run_target(name, spec, cases):
    env = dict(os.environ)
    env.update(spec["env"])
    proc = subprocess.run(
        spec["cmd"], input=json.dumps(cases), capture_output=True, text=True,
        cwd=spec["cwd"], env=env, timeout=600,
    )
    if proc.returncode != 0:
        return None, f"runner exited {proc.returncode}: {proc.stderr.strip()[-2000:]}"
    try:
        return {r["id"]: r for r in json.loads(proc.stdout)}, None
    except (json.JSONDecodeError, KeyError) as error:
        return None, f"unreadable runner output ({error}): {proc.stdout[:500]}"


def _norm(value):
    """JSON equality: 1 == 1.0, but true is not 1."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def judge(case, result):
    """Return (status, problems)."""
    if result is None:
        return "FAIL", ["no result from runner"]
    if "unsupported" in result:
        return "unsupported", [result["unsupported"]]
    expect = case["expect"]
    problems = []

    if "output" in expect:
        if "error" in result:
            problems.append(f"expected output, got error {result['error']!r}")
        elif _norm(result.get("output")) != _norm(expect["output"]):
            problems.append(f"output {result.get('output')!r} != {expect['output']!r}")
    if "error" in expect:
        if "error" not in result:
            problems.append(f"expected an error, got output {result.get('output')!r}")
        elif expect["error"].get("message_contains", "") not in result["error"]:
            problems.append(f"error {result['error']!r} lacks {expect['error']['message_contains']!r}")

    if _norm(result.get("input_after")) != _norm(case["input"]):
        problems.append(f"input was mutated: {result.get('input_after')!r}")

    if "taps" in expect and _norm(result.get("taps")) != _norm(expect["taps"]):
        problems.append(f"taps {result.get('taps')!r} != {expect['taps']!r}")

    if "state" in expect and "state" in result:
        for key, want in expect["state"].items():
            got = result["state"].get(key)
            if got != want:
                problems.append(f"state.{key} {got!r} != {want!r}")

    if "hooks" in expect and "hooks" in result and result["hooks"] != expect["hooks"]:
        problems.append(f"hooks {result['hooks']!r} != {expect['hooks']!r}")

    if problems:
        return "FAIL", problems
    unchecked = [k for k in ("state", "hooks") if k in expect and k not in result]
    if unchecked:
        return "partial", [f"target cannot observe {', '.join(unchecked)}"]
    return "pass", []


def main(argv):
    cases = load_cases()
    names = argv or default_targets()
    report = {"cases": len(cases), "targets": {}}
    matrix = {c["id"]: {} for c in cases}

    for name in names:
        results, error = run_target(name, TARGETS[name], cases)
        if error:
            report["targets"][name] = {"error": error}
            for c in cases:
                matrix[c["id"]][name] = "—"
            continue
        summary = {"pass": 0, "partial": 0, "FAIL": 0, "unsupported": 0, "failures": {}, "unsupported_cases": {}}
        for c in cases:
            status, problems = judge(c, results.get(c["id"]))
            summary[status] += 1
            matrix[c["id"]][name] = status
            if status == "FAIL":
                summary["failures"][c["id"]] = problems
            elif status == "unsupported":
                summary["unsupported_cases"][c["id"]] = problems[0]
        report["targets"][name] = summary

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(report, indent=2))
    (RESULTS / "latest.md").write_text(_markdown(cases, names, matrix, report))
    print(_markdown(cases, names, matrix, report))
    failed = any(t.get("FAIL") or "error" in t for t in report["targets"].values())
    return 1 if failed else 0


def _markdown(cases, names, matrix, report):
    mark = {"pass": "✅", "partial": "✅*", "FAIL": "❌", "unsupported": "➖", "—": "—"}
    lines = ["| case | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for c in cases:
        lines.append(f"| `{c['id']}` | " + " | ".join(mark[matrix[c['id']][n]] for n in names) + " |")
    lines.append("")
    for name in names:
        t = report["targets"][name]
        if "error" in t:
            lines.append(f"- **{name}**: not run: {t['error']}")
        else:
            lines.append(f"- **{name}**: {t['pass']} pass, {t['partial']} pass*, {t['FAIL']} fail, "
                         f"{t['unsupported']} unsupported")
    lines.append("")
    lines.append("✅* passed everything the target can observe; it does not expose State or Hooks "
                 "(the fast mode). ➖ the target cannot express the case.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
