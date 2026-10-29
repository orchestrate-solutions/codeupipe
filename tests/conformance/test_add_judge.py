"""The judge of ``codeupipe add`` (conformance/ADD.md): its verdicts, and its launcher on a fake command."""

import json
import pathlib
import sys
import textwrap

CONFORMANCE = pathlib.Path(__file__).resolve().parents[2] / "conformance"
sys.path.insert(0, str(CONFORMANCE))

from judging.add_launcher import AddLauncher  # noqa: E402
from judging.judge_add_filter import JudgeAddFilter  # noqa: E402

CASE = {"id": "add/a-filter", "args": ["filter", "Discount"],
        "expect": {"exit": 0, "type": "DiscountFilter",
                   "files": {"python": ["discount_filter.py", "tests/test_discount_filter.py"]}}}
REFUSED = {"id": "add/refused", "args": ["valve", "X"],
           "expect": {"exit": 2, "files": {"python": []}, "message_contains": "add_valve"}}


def made(**change):
    """A result in which the command did all that CASE expects."""
    result = {"id": "add/a-filter", "lang": "python", "exit": 0, "stderr": "",
              "printed": ["discount_filter.py", "tests/test_discount_filter.py"],
              "created": ["discount_filter.py", "tests/test_discount_filter.py"], "changed": [],
              "component": "class DiscountFilter:\n    pass\n",
              "lint": [{"cmd": "lint", "exit": 0, "output": "", "quiet": False}],
              "test": {"exit": 1, "output": "AssertionError: Write the acceptance case for DiscountFilter."}}
    result.update(change)
    return result


def verdict(case, result):
    return JudgeAddFilter().judge(case, result)


def test_a_run_that_does_all_that_the_case_expects_passes():
    assert verdict(CASE, made()) == ("pass", [])


def test_each_difference_fails_the_case():
    assert verdict(CASE, made(exit=1))[0] == "FAIL"
    assert verdict(CASE, made(printed=["discount_filter.py"]))[0] == "FAIL"
    assert verdict(CASE, made(created=["discount_filter.py", "extra.py", "tests/test_discount_filter.py"]))[0] == "FAIL"
    assert verdict(CASE, made(component="class Discount:\n"))[0] == "FAIL"
    assert verdict(CASE, made(lint=[{"cmd": "lint", "exit": 1, "output": "CUP-I006", "quiet": False}]))[0] == "FAIL"
    assert verdict(CASE, made(lint=[{"cmd": "gofmt -l", "exit": 0, "output": "a.go", "quiet": True}]))[0] == "FAIL"
    assert verdict(CASE, None)[0] == "FAIL"


def test_the_test_must_fail_with_the_known_message():
    assert verdict(CASE, made(test={"exit": 0, "output": "1 passed"}))[0] == "FAIL"
    assert verdict(CASE, made(test={"exit": 1, "output": "SyntaxError"}))[0] == "FAIL"


def test_a_refusal_writes_nothing_and_says_why():
    refused = {"id": "add/refused", "lang": "python", "exit": 2, "stderr": "use add_valve(predicate, filter)",
               "printed": [], "created": [], "changed": []}
    assert verdict(REFUSED, refused) == ("pass", [])
    assert verdict(REFUSED, dict(refused, created=["x_filter.py"]))[0] == "FAIL"
    assert verdict(REFUSED, dict(refused, stderr="no"))[0] == "FAIL"
    assert verdict(REFUSED, dict(refused, changed=["x_filter.py"]))[0] == "FAIL"


# A fake ``add`` command: it makes the two files of CASE, asks for a line in
# another file on stderr, and refuses a valve. Enough to check the launcher.
FAKE = textwrap.dedent('''
    import pathlib, sys
    kind, name = sys.argv[1], sys.argv[2]
    if kind == "valve":
        print("use add_valve(predicate, filter)", file=sys.stderr)
        sys.exit(2)
    pathlib.Path("tests").mkdir(exist_ok=True)
    pathlib.Path("discount_filter.py").write_text("class DiscountFilter:\\n    pass\\n")
    pathlib.Path("tests/test_discount_filter.py").write_text("x")
    print("discount_filter.py")
    print("tests/test_discount_filter.py")
    print("add to registry.txt: discount_filter", file=sys.stderr)
''')


def fake_target(tmp_path):
    command = tmp_path / "fake_add.py"
    command.write_text(FAKE)
    return {"lang": "python", "cmd": ["{python}", str(command)],
            "setup": {"registry.txt": "made in {project}\n"},
            "lint": [{"cmd": ["{python}", "-c", "import sys; sys.exit(0)"]}],
            "test": {"cmd": ["{python}", "-c",
                             "import pathlib, sys; print(pathlib.Path('registry.txt').read_text());"
                             "print('Write the acceptance case for DiscountFilter.'); sys.exit(1)"]}}


def test_the_launcher_plays_a_case_in_a_project_of_its_own(tmp_path):
    results, error = AddLauncher(tmp_path).run(fake_target(tmp_path), [CASE, REFUSED])
    assert error is None
    made_result, refused = results["add/a-filter"], results["add/refused"]
    # The setup file is there before the command runs, so it is not a file that the command made.
    assert made_result["created"] == ["discount_filter.py", "tests/test_discount_filter.py"]
    assert made_result["printed"] == ["discount_filter.py", "tests/test_discount_filter.py"]
    # The line asked for on stderr is added before the test runs.
    assert "discount_filter" in made_result["test"]["output"]
    assert verdict(CASE, made_result) == ("pass", []), json.dumps(made_result, indent=2)
    assert verdict(REFUSED, refused) == ("pass", [])


def test_the_launcher_sees_a_file_that_the_case_gave_and_the_command_changed(tmp_path):
    given = dict(CASE, given={"python": {"discount_filter.py": "old\n"}},
                 expect=dict(CASE["expect"], exit=1, files={"python": []}))
    results, _ = AddLauncher(tmp_path).run(fake_target(tmp_path), [given])
    found = results["add/a-filter"]
    assert found["changed"] == ["discount_filter.py"]
    assert verdict(given, found)[0] == "FAIL"
