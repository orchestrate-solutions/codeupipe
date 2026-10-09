"""Run the conformance cases against every runtime and judge them one way.

    python conformance/run.py                 # all available targets
    python conformance/run.py python:run go:run

Each runner executes cases and reports what happened. Only this file decides
pass or fail, so every runtime is held to exactly the same comparison.

Result per case and target:
    pass         every expectation matched
    partial      every expectation the target can observe matched, but some
                 (State, Hooks) it does not expose at all (fast static code)
    FAIL         something observable differed (details in the JSON report)
    unsupported  the target cannot express the case (e.g. static export of a
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


def _go():
    return {
        "cmd": ["go", "run", "."],
        # never fetch: the runner builds against the vendored runtimes/go
        "env": {"GOPROXY": "off", "GOFLAGS": "-mod=mod"},
        "cwd": HERE / "runners/go",
        "requires": "go",
    }


def _ts(mode):
    bun = shutil.which("bun") or str(pathlib.Path.home() / ".bun/bin/bun")
    return {
        # Bun runs the vendored runtimes/ts source directly: no npm install.
        # The preload is the step-identity build step (conformance/API.md).
        "cmd": [bun, "run", "--preload", str(REPO / "runtimes/ts/identity/bun_preload.ts"),
                str(HERE / "runners/ts/runner.ts"), mode],
        "env": {},
        "cwd": REPO,
        "requires": bun,
    }


def _cpp():
    build = HERE / "runners/cpp/build"
    return {
        # header-only runtime: compile the runner against runtimes/cpp/include
        "cmd": ["sh", "-c",
                f"mkdir -p '{build}' && c++ -std=c++20 -O2 -I '{REPO}/runtimes/cpp/include' "
                f"'{HERE}/runners/cpp/runner.cpp' -o '{build}/runner' && '{build}/runner'"],
        "env": {},
        "cwd": REPO,
        "requires": "c++",
    }


def _kt():
    build = HERE / "runners/kt/build"
    core = REPO / "runtimes/kt/codeupipe-core/src/main/kotlin/com/codeupipe/core"
    jar = build / "runner.jar"
    return {
        # kotlinc directly (no Gradle download); rebuild only when a source changed
        "cmd": ["sh", "-c",
                f"mkdir -p '{build}' && if [ ! -f '{jar}' ] || [ -n \"$(find '{core}' '{HERE}/runners/kt' "
                f"-name '*.kt' -newer '{jar}')\" ]; then kotlinc '{core}'/*.kt '{HERE}/runners/kt/Runner.kt' "
                f"-include-runtime -nowarn -d '{jar}' >&2 || exit 1; fi; java -jar '{jar}'"],
        "env": {},
        "cwd": REPO,
        "requires": "kotlinc",
    }


def _cs():
    return {
        # the runtime has no package dependencies, so the build restores nothing
        # build output goes to stderr: `dotnet run` would print warnings into the JSON
        "cmd": ["sh", "-c",
                f"dotnet build '{HERE}/runners/cs' -c Release --nologo -v q 1>&2 && "
                f"dotnet '{HERE}/runners/cs/build/bin/Release/net9.0/cs_runner.dll'"],
        "env": {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"},
        "cwd": REPO,
        "requires": "dotnet",
    }


def _rs():
    crate = HERE / "runners/rs"
    return {
        # cargo writes build progress to stderr; stdout carries only the JSON
        "cmd": ["cargo", "run", "--release", "--quiet", "--manifest-path", str(crate / "Cargo.toml")],
        "env": {},
        "cwd": REPO,
        "requires": "cargo",
    }


TARGETS = {
    "python:run": _python("run"),
    "python:run_async": _python("run_async"),
    "python:static-steps": _python("static-steps"),
    "python:static-inline": _python("static-inline"),
    "python:static-observe": _python("static-observe"),
    "go:run": _go(),
    "ts:run": _ts("run"),
    "ts:run_async": _ts("run_async"),
    "cpp:run": _cpp(),
    "kt:run": _kt(),
    "cs:run": _cs(),
    "rs:run": _rs(),
}


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
    tool = spec.get("requires")
    if tool and shutil.which(tool) is None and not pathlib.Path(tool).exists():
        return None, f"{tool} not installed"
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
    names = argv or list(TARGETS)
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
    failed = any(t.get("FAIL") for t in report["targets"].values())
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
                 "(the fast static export). ➖ the target cannot express the case.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
