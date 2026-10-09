"""Python conformance runner: executes cases, reports what happened.

    python runner.py <target> < cases.json > results.json

Targets
    run            codeupipe Pipeline.run (sync, the default)
    run_async      codeupipe Pipeline.run_async (inside asyncio.run)
    static-steps   codeupipe.lower export, per-step layout, loaded from disk
    static-inline  codeupipe.lower export, lowering="inline", loaded from disk
    static-observe codeupipe.lower export, observe=True: State and Hooks too

The runner never judges; conformance/run.py compares every target's results
against the same expectations. The fast static targets have no State or
Hooks, so they omit those fields and the orchestrator skips those checks;
static-observe reports both and is judged on them.
"""

import asyncio
import copy
import importlib
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import conformance_sink as sink  # noqa: E402
import cup_ops as ops  # noqa: E402
from codeupipe import Payload, Pipeline, Valve  # noqa: E402
  # noqa: E402


class Unsupported(Exception):
    pass


def _filter(spec):
    op = spec["op"]
    if op == "set":
        return ops.Set(spec["key"], spec["value"])
    if op == "copy":
        return ops.Copy(spec["from"], spec["to"])
    if op == "add":
        return ops.Add(spec["key"], spec["by"])
    if op == "append":
        return ops.Append(spec["key"], spec["value"])
    if op == "remove":
        return ops.Remove(spec["key"])
    if op == "merge":
        return ops.Merge(spec["value"])
    if op == "has":
        return ops.Has(spec["key"], spec["to"])
    if op == "mutate":
        return ops.Mutate(spec["key"], spec["value"])
    if op == "fail":
        return ops.Fail(spec["message"])
    raise Unsupported(f"unknown filter op {op!r}")


def _tap(spec):
    if spec["op"] == "record":
        return ops.RecordTap(spec["key"])
    if spec["op"] == "fail":
        return ops.FailTap(spec["message"])
    if spec["op"] == "noop":
        return ops.NoopTap()
    raise Unsupported(f"unknown tap op {spec['op']!r}")


def _predicate_source(name, when):
    """Valve predicates are generated as real predicate classes so static
    lowering can recover their source (it refuses anything else)."""
    key = json.dumps(when["key"])
    if when["op"] == "equals":
        body = f"payload.get({key}) == {when['value']!r}"
    elif when["op"] == "truthy":
        body = f"bool(payload.get({key}))"
    else:
        raise Unsupported(f"unknown valve op {when['op']!r}")
    # a predicate object (conformance/API.md, "Valve"): a class with test(),
    # plus a module-level instance under the name the builders look up
    return (f"class When_{name}:\n    def test(self, payload):\n        return {body}\n\n\n"
            f"when_{name} = When_{name}()\n")


def _predicates(steps, module_dir, module_name):
    sources = []

    def walk(items):
        for step in items:
            if step["kind"] == "valve":
                sources.append(_predicate_source(step["name"], step["when"]))
            elif step["kind"] == "pipeline":
                walk(step["steps"])

    walk(steps)
    path = module_dir / f"{module_name}.py"
    path.write_text("\n\n".join(sources) or "\n")
    sys.path.insert(0, str(module_dir))
    try:
        return importlib.import_module(module_name)
    finally:
        sys.path.remove(str(module_dir))


def build(case, cls, predicates, names):
    p = cls()
    for step in case["steps"]:
        kind, name = step["kind"], step["name"]
        if kind == "filter":
            obj = _filter(step)
            p.add_filter(obj)
        elif kind == "tap":
            obj = _tap(step)
            p.add_tap(obj)
        elif kind == "valve":
            obj = Valve(_filter(step["filter"]), getattr(predicates, f"when_{name}"))
            p.add_filter(obj)
        elif kind == "pipeline":
            if not hasattr(p, "add_pipeline"):
                raise Unsupported(f"{cls.__name__} has no add_pipeline")
            obj = build({"steps": step["steps"]}, ops.Nested, predicates, names)
            p.add_pipeline(obj)
        else:
            raise Unsupported(f"unknown step kind {kind!r}")
        names[id(obj)] = name
    return p


def labels(p, names):
    """identity -> the case's step name, for the steps of ``p``.

    Steps are identified by their filter (conformance/API.md), while the
    shared cases name them. The runner built every step, so it knows which
    case step each identity belongs to. An identity reported that is not in
    this map (wrong, or inconsistent between modes) stays as is and fails
    the comparison.
    """
    return {identity: names[id(step)] for identity, step, _type in p._steps}


def _named(steps, label):
    return [label.get(step, step) for step in steps]


def _named_hooks(events, label):
    out = []
    for event in events:
        phase, _, step = event.partition(":")
        out.append(f"{phase}:{label.get(step, step)}")
    return out


def _dynamic(case, predicates, run_async=False):
    names = {}
    p = build(case, Pipeline, predicates, names)
    label = labels(p, names)
    if case.get("hooks"):
        p.use_hook(ops.RecordHook())
    data = copy.deepcopy(case["input"])
    result = {}
    try:
        if run_async:
            out = asyncio.run(p.run_async(Payload(data)))
        else:
            out = p.run(Payload(data))
        result["output"] = out.to_dict()
    except Exception as error:  # noqa: BLE001 — the error is the result
        result["error"] = f"{type(error).__name__}: {error}"
    state = p.state
    result["state"] = {
        "executed": _named(state.executed, label),
        "skipped": _named(state.skipped, label),
        "errors": _named([step for step, _ in state.errors], label),
    }
    if case.get("hooks"):
        result["hooks"] = _named_hooks(sink.HOOKS, label)
    result["input_after"] = data
    return result


def _load_export(p, lowering, observe, workdir):
    """Export ``p`` and import the package from disk, as a customer would."""
    from codeupipe.lower import build_export_pipeline_v2

    out = build_export_pipeline_v2(write=False).run(
        Payload({"pipeline": p, "pattern": "flat", "lowering": lowering, "observe": observe}))
    for f in out.get("files") or []:
        target = workdir / f["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f["content"])
    package_parent = str(workdir / "src")
    for name in [m for m in sys.modules if m == "steps" or m.startswith("steps.")]:
        del sys.modules[name]
    sys.path.insert(0, package_parent)
    try:
        return importlib.import_module("steps")
    finally:
        sys.path.remove(package_parent)


def _static(case, predicates, lowering, workdir, observe=False):
    names = {}
    p = build(case, Pipeline, predicates, names)
    label = labels(p, names)
    hooks = [ops.RecordHook()] if observe and case.get("hooks") else None
    if hooks:
        p.use_hook(hooks[0])
    package = _load_export(p, lowering, observe, workdir)
    data = copy.deepcopy(case["input"])
    result = {}
    state = {}
    try:
        if observe:
            result["output"] = package.run(data, state=state, hooks=hooks)
        else:
            result["output"] = package.run(data)
    except Exception as error:  # noqa: BLE001
        result["error"] = f"{type(error).__name__}: {error}"
    if observe:
        result["state"] = {
            "executed": _named(state["executed"], label),
            "skipped": _named(state["skipped"], label),
            "errors": _named([step for step, _ in state["errors"]], label),
        }
        if case.get("hooks"):
            result["hooks"] = _named_hooks(sink.HOOKS, label)
    result["input_after"] = data
    return result


def run_case(case, target, index):
    sink.reset()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cup_conf_"))
    try:
        predicates = _predicates(case["steps"], tmp, f"conf_predicates_{index}")
        if target == "run":
            result = _dynamic(case, predicates)
        elif target == "run_async":
            result = _dynamic(case, predicates, run_async=True)
        elif target in ("static-steps", "static-inline"):
            result = _static(case, predicates, target.split("-", 1)[1], tmp)
        elif target == "static-observe":
            result = _static(case, predicates, "steps", tmp, observe=True)
        else:
            raise SystemExit(f"unknown target {target!r}")
    except Unsupported as reason:
        return {"id": case["id"], "unsupported": str(reason)}
    except Exception as error:  # noqa: BLE001 — e.g. export refusing a shape
        return {"id": case["id"], "unsupported": f"{type(error).__name__}: {error}"}
    result["id"] = case["id"]
    result["taps"] = list(sink.TAPS)
    return result


BENCH_WARMUP = 20000
BENCH_RUNS = 20000
BENCH_REPEATS = 5


_REFERENCE_KEYS = tuple("k%d" % i for i in range(10))


def _reference_write(data, key):
    data[key] = data.get(key, 0) + 1
    return data


def _reference():
    """The reference workload: ten dict writes behind ten function calls,
    with no framework. A pipeline's time is reported relative to it."""
    data = {"a": 1}
    for key in _REFERENCE_KEYS:
        data = _reference_write(data, key)
    return data


def _timed(fn):
    import time
    t0 = time.perf_counter()
    for _ in range(BENCH_RUNS):
        fn()
    return time.perf_counter() - t0


def _measure(fn):
    """(µs per run, time relative to the reference workload).

    µs per run is the best of BENCH_REPEATS x BENCH_RUNS. The relative time
    is for comparing runs on different machines and under different load:
    each repeat times the reference workload and then ``fn``, back to back,
    so whatever slows one slows the other, and the median of the repeats'
    ratios is reported.
    """
    import statistics
    for _ in range(BENCH_WARMUP):
        fn()
        _reference()
    best, ratios = None, []
    for _ in range(BENCH_REPEATS):
        reference = _timed(_reference)
        elapsed = _timed(fn)
        ratios.append(elapsed / reference)
        best = elapsed if best is None else min(best, elapsed)
    return best / BENCH_RUNS * 1e6, statistics.median(ratios)


def bench(target, scenarios):
    results = []
    for index, case in enumerate(scenarios):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="cup_bench_"))
        predicates = _predicates(case["steps"], tmp, f"bench_predicates_{index}")
        p = build(case, Pipeline, predicates, {})
        if case.get("hooks") == "noop":
            p.use_hook(ops.NoopHook())
        data = case["input"]
        if target == "run":
            fn = lambda: p.run(Payload(dict(data)))  # noqa: E731
            output = fn().to_dict()
        elif target in ("static-inline", "static-steps"):
            try:
                run = _load_export(p, target.split("-", 1)[1], False, tmp).run
            except Exception as error:  # noqa: BLE001 — export refused the shape (e.g. Hooks)
                results.append({"id": case["id"], "unsupported": f"{type(error).__name__}: {error}"})
                continue
            fn = lambda: run(dict(data))  # noqa: E731
            output = fn()
        elif target == "static-observe":
            run = _load_export(p, "steps", True, tmp).run
            hooks = [ops.NoopHook()] if case.get("hooks") == "noop" else None
            state = {}
            fn = lambda: run(dict(data), state=state, hooks=hooks)  # noqa: E731
            output = fn()
        else:
            raise SystemExit(f"unknown bench target {target!r}")
        us_per_run, relative = _measure(fn)
        results.append({"id": case["id"], "us_per_run": us_per_run, "relative": relative, "output": output})
    return results


def main():
    target = sys.argv[1]
    if target.startswith("bench:"):
        json.dump(bench(target.split(":", 1)[1], json.load(sys.stdin)), sys.stdout)
        return
    cases = json.load(sys.stdin)
    json.dump([run_case(case, target, i) for i, case in enumerate(cases)], sys.stdout)


if __name__ == "__main__":
    main()
