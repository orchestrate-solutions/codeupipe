"""Type-strict structural equality.

Python's ``==`` says ``{"a": True} == {"a": 1} == {"a": 1.0}``. An export
that turned a bool into an int would pass a plain ``==`` check, so the
scorecard compares types as well as values, and top-level key order.
"""

__all__ = ["strict_equal", "first_difference"]


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def first_difference(a, b, path="$"):
    """None if ``a`` and ``b`` are strictly equal, else a description of the
    first place they differ."""
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__} ({a!r} vs {b!r})"
    if isinstance(a, dict):
        if list(a) != list(b):
            if set(a) != set(b):
                return f"{path}: keys {sorted(map(repr, a))} != {sorted(map(repr, b))}"
            return f"{path}: key order {list(a)!r} != {list(b)!r}"
        for key in a:
            diff = first_difference(a[key], b[key], f"{path}[{key!r}]")
            if diff:
                return diff
        return None
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            diff = first_difference(x, y, f"{path}[{i}]")
            if diff:
                return diff
        return None
    if isinstance(a, float) and a != a and b != b:  # NaN is equal to itself here
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"
    return None


def strict_equal(a, b):
    return first_difference(a, b) is None
