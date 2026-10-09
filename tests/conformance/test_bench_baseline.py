"""The speed check: each benchmark number against its recorded baseline.

A number is compared as a ratio to a reference workload timed beside it, so
the check does not depend on how fast or how busy the machine is.
"""

import pathlib
import subprocess
import sys

import pytest

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))
import bench  # noqa: E402

BASE = {"relative": {"python:run": {"micro-pass": 5.0, "taps": 6.0},
                     "python:static-inline": {"micro-pass": 0.5}}}


def _now(micro_pass=5.0):
    """The baseline's ratios again, with python:run micro-pass replaced."""
    return {"relative": {"python:run": {"micro-pass": micro_pass, "taps": 6.0},
                         "python:static-inline": {"micro-pass": 0.5}}}


def test_the_same_numbers_pass():
    assert bench.compare(BASE, _now(), tolerance=25) == []


def test_a_number_inside_the_band_passes():
    assert bench.compare(BASE, _now(micro_pass=6.0), tolerance=25) == []   # +20%
    assert bench.compare(BASE, _now(micro_pass=4.0), tolerance=25) == []   # -20%


def test_a_slower_number_fails_and_says_by_how_much():
    [problem] = bench.compare(BASE, _now(micro_pass=7.0), tolerance=25)    # +40%
    assert problem["target"] == "python:run" and problem["scenario"] == "micro-pass"
    assert problem["kind"] == "slower"
    assert round(problem["change_percent"]) == 40


def test_a_faster_number_also_fails_so_the_baseline_is_recorded_again():
    [problem] = bench.compare(BASE, _now(micro_pass=3.0), tolerance=25)    # -40%
    assert problem["kind"] == "faster"
    assert round(problem["change_percent"]) == -40


def test_a_missing_number_fails():
    now = _now()
    del now["relative"]["python:run"]["taps"]
    [problem] = bench.compare(BASE, now, tolerance=25)
    assert problem["kind"] == "missing" and problem["scenario"] == "taps"


def test_a_new_number_with_no_baseline_fails():
    now = _now()
    now["relative"]["python:run"]["new-scenario"] = 1.0
    [problem] = bench.compare(BASE, now, tolerance=25)
    assert problem["kind"] == "not recorded" and problem["scenario"] == "new-scenario"


def test_the_baseline_file_holds_a_ratio_for_every_number():
    baseline = bench.load_baseline()
    assert baseline, "run: python conformance/bench.py --record"
    for version, recorded in baseline.items():
        assert set(recorded["relative"]) == set(bench.BENCH_TARGETS), version
        for target, row in recorded["relative"].items():
            assert row and all(ratio > 0 for ratio in row.values()), (version, target)


@pytest.mark.perf
def test_nothing_is_slower_or_faster_than_its_baseline():
    if bench.python_key() not in bench.load_baseline():
        pytest.skip("no baseline for Python %s: python conformance/bench.py --record" % bench.python_key())
    done = subprocess.run([sys.executable, str(CONFORMANCE / "bench.py"), "--check"],
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-2000:]
