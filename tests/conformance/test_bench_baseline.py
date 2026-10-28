"""The comparison of benchmark numbers with a recorded baseline
(bench.py --check). No test and no CI job runs the comparison itself: a
shared machine is too noisy to judge speed. It is kept for a machine whose
resources are fixed, such as a constrained container.

A number is compared as a ratio to a reference workload timed beside it.
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
    for key, recorded in baseline.items():
        runtime = "rust" if key == "rust" else "python"   # the other keys are Python versions
        want = {target for target in bench.BENCH_TARGETS if target.split(":")[0] == runtime}
        assert set(recorded["relative"]) == want, key
        for target, row in recorded["relative"].items():
            assert row and all(ratio > 0 for ratio in row.values()), (key, target)


def test_a_rust_number_is_kept_apart_from_the_python_version():
    # The speed of the Rust runtime does not depend on the Python that runs bench.py.
    assert bench.baseline_key("python:run", python="3.12") == "3.12"
    assert bench.baseline_key("rust:run", python="3.12") == "rust"


def test_the_check_compares_each_target_with_its_own_baseline():
    baseline = {"3.12": {"relative": {"python:run": {"m": 5.0}, "python:static-inline": {"m": 0.5}}},
                "3.9": {"relative": {"python:run": {"m": 9.0}}},
                "rust": {"relative": {"rust:run": {"m": 1.0}}}}
    assert bench.baseline_for(baseline, ["python:run", "rust:run"], python="3.12") == {
        "relative": {"python:run": {"m": 5.0}, "rust:run": {"m": 1.0}}}


def test_a_record_replaces_only_the_targets_that_were_measured():
    baseline = {"3.12": {"relative": {"python:run": {"m": 5.0}}, "us_per_run": {"python:run": {"m": 4.0}}}}
    now = {"relative": {"rust:run": {"m": 1.0}}, "us_per_run": {"rust:run": {"m": 0.9}}}
    bench.record_into(baseline, now, python="3.12")
    assert baseline == {"3.12": {"relative": {"python:run": {"m": 5.0}}, "us_per_run": {"python:run": {"m": 4.0}}},
                        "rust": {"relative": {"rust:run": {"m": 1.0}}, "us_per_run": {"rust:run": {"m": 0.9}}}}
