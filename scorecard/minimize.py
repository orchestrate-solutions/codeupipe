"""Shrink a failing case to a small reproducer (greedy delta debugging).

``minimize(case, still_fails)`` repeatedly tries smaller variants and keeps
any for which ``still_fails(variant)`` is true, until none helps:

- drop a step (at any nesting depth)
- replace a nested pipeline by its steps, or a Valve by its filter
- drop an input key, or turn Hooks off
- rename a step to a plain unique name (keeps the name only if it matters)
"""

import copy
import itertools

__all__ = ["minimize", "candidates"]


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def _step_lists(steps, path=()):
    """(path, list) for the top-level list and every nested pipeline's list."""
    yield path, steps
    for i, step in enumerate(steps):
        if step["kind"] == "pipeline":
            yield from _step_lists(step["steps"], path + (i,))


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def _resolve(case, path):
    steps = case["steps"]
    for i in path:
        steps = steps[i]["steps"]
    return steps


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def candidates(case):
    """Smaller variants of ``case``, most aggressive first."""
    for path, steps in list(_step_lists(case["steps"])):
        for i in range(len(steps)):
            variant = copy.deepcopy(case)
            del _resolve(variant, path)[i]
            yield variant
    for path, steps in list(_step_lists(case["steps"])):
        for i, step in enumerate(steps):
            if step["kind"] == "pipeline":
                variant = copy.deepcopy(case)
                target = _resolve(variant, path)
                target[i:i + 1] = target[i]["steps"]
                yield variant
            elif step["kind"] == "valve":
                variant = copy.deepcopy(case)
                target = _resolve(variant, path)
                replacement = {"kind": "filter", "name": step["name"]}
                replacement.update(step["filter"])
                target[i] = replacement
                yield variant
    for key in list(case["input"]):
        variant = copy.deepcopy(case)
        del variant["input"][key]
        yield variant
    if case.get("hooks"):
        variant = copy.deepcopy(case)
        variant["hooks"] = False
        yield variant
    taken = {s["name"] for _, steps in _step_lists(case["steps"]) for s in steps}
    fresh = (f"m{n}" for n in itertools.count() if f"m{n}" not in taken)
    for path, steps in list(_step_lists(case["steps"])):
        for i, step in enumerate(steps):
            if not (step["name"].startswith("m") and step["name"][1:].isdigit()):
                variant = copy.deepcopy(case)
                _resolve(variant, path)[i]["name"] = next(fresh)
                yield variant


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def minimize(case, still_fails, max_attempts=400):
    current = copy.deepcopy(case)
    attempts = 0
    improved = True
    while improved and attempts < max_attempts:
        improved = False
        for variant in candidates(current):
            attempts += 1
            if attempts > max_attempts:
                break
            if still_fails(variant):
                current = variant
                improved = True
                break
    current["id"] = case["id"] + "/min"
    return current
