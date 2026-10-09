"""Judge one mode's record against the dynamic reference.

``divergences(dynamic, record, mode)`` returns a list of ``{"check", "detail"}``;
empty means the mode agrees on everything it can observe. A refusal is not
judged here: the caller counts it separately (it is not a pass).
"""

from scorecard.strict import first_difference

__all__ = ["divergences", "self_checks", "verdict"]


def _diff(check, a, b, out):
    detail = first_difference(a, b)
    if detail:
        out.append({"check": check, "detail": detail})


def self_checks(record, who):
    """Checks a run makes of itself: input untouched, reruns identical."""
    out = []
    if record.get("input_diff"):
        out.append({"check": "input_mutated", "detail": f"{who}: {record['input_diff']}"})
    if record.get("rerun_diff"):
        out.append({"check": "rerun_differs", "detail": f"{who}: {record['rerun_diff']}"})
    return out


def divergences(dynamic, record, mode):
    out = []
    if record["status"] == "crash":
        return [{"check": "export_crashed", "detail": record["reason"]}]
    if record["status"] == "refused":
        return []
    _diff("outcome", [dynamic["output"], dynamic["error"]], [record["output"], record["error"]], out)
    _diff("taps", dynamic["taps"], record["taps"], out)
    out.extend(self_checks(record, mode))
    if mode == "observe":
        for key in ("executed", "skipped", "errors", "timing_keys"):
            _diff(f"state.{key}", dynamic["state"][key], record["state"][key], out)
        _diff("hooks", dynamic["hooks"], record["hooks"], out)
        if record.get("source_hooks_guard"):
            out.append({"check": "source_hooks_guard", "detail": record["source_hooks_guard"]})
    if "hooks_refused" in record and not record["hooks_refused"]:
        out.append({"check": "hooks_not_refused",
                    "detail": record.get("hooks_refused_detail", "fast export of a hooked pipeline did not refuse")})
    return out


def verdict(record, found):
    if found:
        return "fail"
    return "refused" if record["status"] == "refused" else "pass"
