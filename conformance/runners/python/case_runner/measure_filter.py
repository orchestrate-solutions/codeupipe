"""MeasureFilter: how long one run takes."""

import statistics
import time

from codeupipe import Payload

WARMUP = 20000
RUNS = 20000
REPEATS = 5

_REFERENCE_KEYS = tuple("k%d" % i for i in range(10))


def _reference_write(data, key):
    data[key] = data.get(key, 0) + 1
    return data


class MeasureFilter:
    """Filter (sync).

    Input keys: ``fn`` (from MakeRunFunctionFilter).
    Output keys: ``us_per_run`` (µs for one run: the best of REPEATS x RUNS)
    and ``relative`` (the time of ``fn`` as a ratio to a reference workload).

    The relative time is for comparing runs on different machines and under
    different load: each repeat times the reference workload and then
    ``fn``, back to back, so whatever slows one slows the other, and the
    median of the ratios of the repeats is reported.
    """

    def call(self, payload: Payload) -> Payload:
        us_per_run, relative = self.measure(payload.get("fn"))
        return payload.insert("us_per_run", us_per_run).insert("relative", relative)

    def measure(self, fn):
        for _ in range(WARMUP):
            fn()
            self.reference()
        best, ratios = None, []
        for _ in range(REPEATS):
            reference = self.timed(self.reference)
            elapsed = self.timed(fn)
            ratios.append(elapsed / reference)
            best = elapsed if best is None else min(best, elapsed)
        return best / RUNS * 1e6, statistics.median(ratios)

    def timed(self, fn) -> float:
        started = time.perf_counter()
        for _ in range(RUNS):
            fn()
        return time.perf_counter() - started

    @staticmethod
    def reference():
        """The reference workload: ten dict writes behind ten function calls, with no framework."""
        data = {"a": 1}
        for key in _REFERENCE_KEYS:
            data = _reference_write(data, key)
        return data
