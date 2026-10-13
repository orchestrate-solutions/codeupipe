"""CUP-I008: logic that is not in a primitive. A warning."""

from codeupipe_lint.invariants.lint_pipeline import lint_paths
from codeupipe_lint.invariants.__main__ import main


def lint(tmp_path, files, **options):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    out = lint_paths([str(tmp_path)], **options)
    found = ["%s:%d %s" % (f.path[len(str(tmp_path)) + 1:], f.line, f.rule) for f in out.get("findings")]
    return out, found


def test_a_function_with_a_decision_that_is_not_in_a_primitive_is_a_warning(tmp_path):
    out, found = lint(tmp_path, {"who_is_due.py": (
        'def who_is_due(entries):\n    if not entries:\n        return "say"\n    return "model"\n'
        "def pick(items):\n    for each in items:\n        return each\n"
        'def choose(flag):\n    return "a" if flag else "b"\n'
        "async def load(path):\n    try:\n        return await read(path)\n    except OSError:\n        return None\n"
        "def wait(queue):\n    while queue:\n        queue.pop()\n"
        "def plain(a, b):\n    return a + b\n"
        "def evens(items):\n    return [each for each in items if each % 2 == 0]\n")})
    assert found == ["who_is_due.py:1 CUP-I008", "who_is_due.py:5 CUP-I008", "who_is_due.py:8 CUP-I008",
                     "who_is_due.py:10 CUP-I008", "who_is_due.py:15 CUP-I008"]
    first = out.get("findings")[0]
    assert first.severity == "warning"
    assert first.message.startswith("Function `who_is_due` has logic and is not a Filter, a Predicate, a Tap, "
                                    "a Hook or a Pipeline. Write it as a primitive")
    assert "CUP-I008 logic-outside-primitive  warning: Function `who_is_due`" in out.get("report")


def test_a_class_that_is_not_a_primitive_and_code_at_the_top_of_a_file(tmp_path):
    _, found = lint(tmp_path, {
        "record_store.py": (
            "class RecordStore:\n    def read(self, name):\n        if name not in self.files:\n"
            "            raise KeyError(name)\n        return []\n"
            "class Point:\n    def __init__(self, x):\n        self.x = x\n"),
        "main.py": "import sys\nARGS = sys.argv[1:]\nif not ARGS:\n    sys.exit(2)\nfor arg in ARGS:\n    print(arg)\n"})
    assert found == ["main.py:3 CUP-I008", "record_store.py:1 CUP-I008"]


def test_logic_in_a_primitive_is_where_it_must_be(tmp_path):
    _, found = lint(tmp_path, {
        "pick_filter.py": ("class PickFilter:\n    def call(self, payload):\n        if payload.get('a'):\n"
                           "            return payload.insert('b', 1)\n        return payload\n"),
        "is_on_predicate.py": "class IsOnPredicate:\n    def test(self, payload):\n        return True if payload.get('on') else False\n",
        "order_pipeline.py": ("from codeupipe import Pipeline\nclass OrderPipeline(Pipeline):\n    def __init__(self):\n"
                              "        super().__init__()\n        for step in ():\n            self.add_filter(step)\n")})
    assert found == []


def test_the_usual_guards_at_the_top_of_a_file_are_not_logic(tmp_path):
    _, found = lint(tmp_path, {"entry.py": (
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import ast\n"
        "def main():\n    return 0\n"
        'if __name__ == "__main__":\n    raise SystemExit(main())\n')})
    assert found == []


def test_a_test_file_is_not_checked(tmp_path):
    _, found = lint(tmp_path, {"test_pick.py": "def test_pick():\n    for each in ():\n        assert each\n"})
    assert found == []


def test_a_comment_allows_plain_logic(tmp_path):
    out, found = lint(tmp_path, {"shell.py": (
        "# cup: allow-plain the edge to the shell\n"
        "def run(command):\n    try:\n        return start(command)\n    except OSError:\n        return None\n")})
    assert found == []
    assert len(out.get("suppressed")) == 1


def test_a_warning_fails_the_run_only_when_it_is_strict(tmp_path, capsys):
    (tmp_path / "pick.py").write_text("def pick(flag):\n    return 1 if flag else 2\n")
    assert main([str(tmp_path)]) == 0
    assert "No invariant violations. 1 warning." in capsys.readouterr().out
    assert main(["--strict", str(tmp_path)]) == 1
    assert main(["--strict", "--disable", "CUP-I008", str(tmp_path)]) == 0
