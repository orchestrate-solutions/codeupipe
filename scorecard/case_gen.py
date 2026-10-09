"""Seeded generator of random pipelines and inputs in the conformance
vocabulary (conformance/README.md). Stdlib only: ``random.Random(seed)``.

A generated case has the conformance case shape (``id``, ``steps``,
``input``, ``hooks``), so a failing one can be pasted straight into
conformance/cases/*.json.

Coverage, by construction:
- every filter op: set copy add append remove merge has mutate fail
- every tap op: record noop fail
- Valves with ``equals`` and ``truthy`` predicates, around any filter op
- nested pipelines (up to ``max_depth``), including empty ones
- ``hooks: true`` on a share of cases
- keys drawn from a small shared pool so steps read what others wrote,
  including keys that are awkward in source code (quotes, spaces, unicode)
- values of every JSON type, nested; ``add`` sometimes gets operands that
  make it raise, so error parity is exercised too
- optionally (``hostile_rate``) step names a developer could plausibly
  pick but that are awkward for generated code: builtins, names the
  exported ``run()`` binds, duplicates, non-identifiers.
"""

import random

__all__ = ["generate_case", "generate_cases", "generate_input", "generate_value", "KEYS", "HOSTILE_NAMES"]

FILTER_OPS = ["set", "copy", "add", "append", "remove", "merge", "has", "mutate", "fail"]
TAP_OPS = ["record", "noop", "fail"]

KEYS = ["a", "b", "n", "items", "flag", "user", "é", "with space", "q'\"uote", "back\\slash", "0"]

# Plausible step names that stress code generation. Each is accepted by the
# dynamic Pipeline, so the export must either reproduce it or refuse it.
HOSTILE_NAMES = [
    # names the observable run() binds as locals
    "run", "data", "state", "hooks", "timing", "trace_id", "executed", "skipped", "errors",
    "timings", "SOURCE_HOOKS",
    # builtins the generated step bodies call
    "list", "dict", "bool", "len", "Exception",
    # names generated modules define or import
    "TAPS", "pipeline", "steps", "mutable",
    # ordinary names that collide with each other
    "validate", "validate", "inner__x", "check", "check_predicate",
    # not Python identifiers
    "load-user", "two words", "class", "a.b", "1st",
]


def generate_value(rng, depth=0):
    """A JSON-shaped value (None, bool, int, float, str, list, dict)."""
    roll = rng.random()
    if depth < 2 and roll < 0.12:
        return [generate_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if depth < 2 and roll < 0.22:
        return {rng.choice(KEYS): generate_value(rng, depth + 1) for _ in range(rng.randint(0, 3))}
    return rng.choice([
        None, True, False, 0, 1, -7, 2 ** 40, 0.5, -1.25,
        "", "x", "héllo", "q'\"", "multi\nline", "0",
    ])


def generate_input(rng):
    return {rng.choice(KEYS): generate_value(rng) for _ in range(rng.randint(0, 5))}


def _add_operand(rng):
    # numbers mostly; a string/list/None sometimes, which raises (or concatenates)
    return rng.choice([1, 1, 2, -3, 0.5, 10 ** 20, True, "s", [1], None])


def _filter_spec(rng):
    op = rng.choices(FILTER_OPS, weights=[5, 3, 4, 3, 3, 2, 2, 2, 1])[0]
    key = rng.choice(KEYS)
    if op == "set":
        return {"op": op, "key": key, "value": generate_value(rng)}
    if op == "copy":
        return {"op": op, "from": key, "to": rng.choice(KEYS)}
    if op == "add":
        return {"op": op, "key": key, "by": _add_operand(rng)}
    if op == "append":
        return {"op": op, "key": key, "value": generate_value(rng)}
    if op == "remove":
        return {"op": op, "key": key}
    if op == "merge":
        return {"op": op, "value": {rng.choice(KEYS): generate_value(rng) for _ in range(rng.randint(0, 3))}}
    if op == "has":
        return {"op": op, "key": key, "to": rng.choice(KEYS)}
    if op == "mutate":
        return {"op": op, "key": key, "value": generate_value(rng)}
    return {"op": "fail", "message": rng.choice(["boom", "bad 'input'", "ünïcode"])}


def _when(rng):
    if rng.random() < 0.5:
        return {"op": "truthy", "key": rng.choice(KEYS)}
    return {"op": "equals", "key": rng.choice(KEYS), "value": rng.choice([0, 1, True, None, "x", "", [1], {"a": 1}])}


def _namer(rng, hostile):
    """next_name(prefix): unique ``prefix<n>``, or sometimes a hostile name."""
    counter = [0]

    def next_name(prefix):
        counter[0] += 1
        if hostile and rng.random() < 0.35:
            return rng.choice(HOSTILE_NAMES)
        return f"{prefix}{counter[0]}"
    return next_name


def _steps(rng, names, depth, max_steps, max_depth):
    out = []
    for _ in range(rng.randint(0, max_steps)):
        roll = rng.random()
        if roll < 0.55:
            step = {"kind": "filter", "name": names("s")}
            step.update(_filter_spec(rng))
        elif roll < 0.72:
            op = rng.choices(TAP_OPS, weights=[5, 2, 2])[0]
            step = {"kind": "tap", "name": names("t"), "op": op}
            if op == "record":
                step["key"] = rng.choice(KEYS)
            elif op == "fail":
                step["message"] = "sink down"
        elif roll < 0.92 or depth >= max_depth:
            step = {"kind": "valve", "name": names("v"), "when": _when(rng), "filter": _filter_spec(rng)}
        else:
            step = {"kind": "pipeline", "name": names("p"),
                    "steps": _steps(rng, names, depth + 1, max(1, max_steps // 2), max_depth)}
        out.append(step)
    return out


def generate_case(rng, index=0, max_steps=8, max_depth=2, hostile_rate=0.0):
    """One random case. ``rng`` is a ``random.Random``; same seed, same case.

    One case in 20 is long (up to 40 steps) so the dynamic Payload's overlay
    chain crosses its flattening depth (32 writes).
    """
    hostile = rng.random() < hostile_rate
    names = _namer(rng, hostile)
    limit = 40 if rng.random() < 0.05 else max_steps
    return {
        "id": f"random/{index}",
        "hooks": rng.random() < 0.4,
        "hostile_names": hostile,
        "steps": _steps(rng, names, 0, limit, max_depth),
        "input": generate_input(rng),
    }


def generate_cases(seed, count, **kwargs):
    rng = random.Random(seed)
    return [generate_case(rng, i, **kwargs) for i in range(count)]
