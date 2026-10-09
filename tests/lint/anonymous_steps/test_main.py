"""``python -m codeupipe_lint.anonymous_steps <paths...>``."""

import os
import subprocess
import sys

from codeupipe_lint.anonymous_steps.__main__ import main

from ._support import REPO, fixture


def test_main_prints_findings_and_returns_one(capsys):
    code = main([fixture("python", "probe.py")])
    out = capsys.readouterr().out
    assert code == 1
    assert "probe.py:31:14  CUP-A001 lambda-step  Filter is a lambda." in out


def test_main_clean_returns_zero(capsys):
    assert main([fixture("python", "negative.py")]) == 0
    assert "No anonymous steps." in capsys.readouterr().out


def test_exclude_option(capsys):
    assert main(["--exclude", "*/probe.py", fixture("python", "probe.py")]) == 0


def test_list_rules(capsys):
    assert main(["--rules"]) == 0
    out = capsys.readouterr().out
    assert "CUP-A001  lambda-step" in out and "CUP-A008  function-predicate" in out


def test_runs_as_a_module():
    env = dict(os.environ, PYTHONPATH=REPO)
    proc = subprocess.run([sys.executable, "-m", "codeupipe_lint.anonymous_steps", fixture("python", "probe.py")],
                          cwd=REPO, env=env, capture_output=True, text=True)
    assert proc.returncode == 1, proc.stderr
    assert "CUP-A003 local-type-step" in proc.stdout
