"""Run one case in each execution mode and record everything observable.

Modes
    dynamic   codeupipe ``Pipeline.run`` (the reference)
    steps     fast export, per-step layout: ``run(data)``
    inline    fast export, inline layout: ``run(data)``
    observe   observable export: ``run(data, state=, hooks=, timing=True)``

Each returns a record (plain dict, JSON-serialisable apart from the hook
snapshots, which are JSON-shaped anyway):

    status        "ok" | "refused" (UnsupportedFilterShape at export)
                  | "crash" (any other exception while exporting or loading)
    output/error  the returned dict, or "Type: message"
    taps          what the reference Taps recorded (conformance_sink.TAPS)
    input_diff    None, or where the caller's input was changed
    rerun_diff    None, or where a second run on a fresh copy of the same
                  input differed from the first (state leaking across runs)
    state         executed / skipped / errors [(name, "Type: message")] /
                  timing keys (dynamic, observe)
    hooks         SnapshotHook event sequence (dynamic, observe)
"""

import copy
import traceback

from scorecard import vocab
from scorecard.snapshot_hook import SnapshotHook
from scorecard.strict import first_difference

__all__ = ["run_dynamic", "run_fast", "run_observe", "describe_error"]


def describe_error(error):
    return f"{type(error).__name__}: {error}"


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def _call(fn, data):
    vocab.sink.reset()
    try:
        return fn(data), None, list(vocab.sink.TAPS)
    except Exception as error:  # noqa: BLE001 — the error is the result
        return None, describe_error(error), list(vocab.sink.TAPS)


def _run_twice(fn, case):
    """Run on a deep copy of the input; check the copy is untouched; run
    again on another copy and check the second run is identical."""
    data = copy.deepcopy(case["input"])
    output, error, taps = _call(fn, data)
    record = {"status": "ok", "output": output, "error": error, "taps": taps,
              "input_diff": first_difference(case["input"], data)}
    output2, error2, taps2 = _call(fn, copy.deepcopy(case["input"]))
    record["rerun_diff"] = first_difference([output, error, taps], [output2, error2, taps2])
    return record


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def _export(pipeline, lowering, observe):
    try:
        return vocab.load_export(pipeline, lowering, observe, vocab.new_workdir()), None
    except vocab.UnsupportedFilterShape as refusal:
        return None, {"status": "refused", "reason": str(refusal)}
    except Exception as error:  # noqa: BLE001 — export or import crashed
        return None, {"status": "crash", "reason": describe_error(error),
                      "trace": traceback.format_exc(limit=-3)}


def _state_record(executed, skipped, errors, timings):
    return {"executed": list(executed), "skipped": list(skipped),
            "errors": [[name, describe_error(err)] for name, err in errors],
            "timing_keys": list(timings)}


def run_dynamic(case, predicates):
    holder = {}

    def fn(data):
        hook = SnapshotHook()
        pipeline = vocab.build_pipeline(case, predicates, hooks=[hook])
        pipeline.observe(timing=True)
        holder.update(hook=hook, pipeline=pipeline)
        return pipeline.run(vocab.Payload(data)).to_dict()

    record = _run_twice(fn, case)
    # the second run's hook/state are the ones kept; the rerun check above
    # already proved both runs agree on output, error and taps
    state = holder["pipeline"].state
    record["state"] = _state_record(state.executed, state.skipped, state.errors, state.timings)
    record["hooks"] = holder["hook"].sequence()
    return record


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def run_fast(case, predicates, lowering):
    """Fast export. A case with Hooks must be *refused* (documented); the
    same pipeline without Hooks is then exported and compared on output,
    taps and input, since Hooks cannot change those."""
    extra = {}
    if case.get("hooks"):
        hooked = vocab.build_pipeline(case, predicates, hooks=[SnapshotHook()])
        package, failure = _export(hooked, lowering, False)
        extra["hooks_refused"] = failure is not None and failure["status"] == "refused"
        if package is not None:
            extra["hooks_refused_detail"] = "exported a pipeline with Hooks instead of refusing"
    package, failure = _export(vocab.build_pipeline(case, predicates), lowering, False)
    if failure:
        failure.update(extra)
        return failure
    record = _run_twice(package.run, case)
    record.update(extra)
    return record


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def run_observe(case, predicates):
    """Observable export. The pipeline carries the case's Hooks (so
    SOURCE_HOOKS is exercised); a SnapshotHook is passed at run time
    either way, so every case gets the hook parity check."""
    source_hooks = [SnapshotHook()] if case.get("hooks") else []
    package, failure = _export(vocab.build_pipeline(case, predicates, hooks=source_hooks), "steps", True)
    if failure:
        return failure
    holder = {}

    def fn(data):
        hook = SnapshotHook()
        state = {}
        holder.update(hook=hook, state=state)
        return package.run(data, state=state, hooks=[hook], timing=True)

    record = _run_twice(fn, case)
    state = holder["state"]
    record["state"] = _state_record(state["executed"], state["skipped"], state["errors"], state["timings"])
    record["hooks"] = holder["hook"].sequence()
    if case.get("hooks"):
        try:
            package.run(copy.deepcopy(case["input"]))
            record["source_hooks_guard"] = "run() without hooks= did not raise"
        except TypeError as error:
            record["source_hooks_guard"] = (None if "exported with Hooks" in str(error)
                                            else f"TypeError, but not the guard: {error}")
        except Exception as error:  # noqa: BLE001
            record["source_hooks_guard"] = f"raised {describe_error(error)}, not TypeError"
    return record
