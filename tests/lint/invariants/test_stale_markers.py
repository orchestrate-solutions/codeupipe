"""CUP-I009: a comment that allows nothing. A warning."""

from codeupipe_lint.invariants.__main__ import main

from .test_plain_logic import lint


def test_a_comment_that_allows_nothing_is_a_warning(tmp_path):
    out, found = lint(tmp_path, {"add.py": (
        "# cup: allow-plain it had a loop before\n"
        "def add(a, b):\n    return a + b\n"
        "ONE = 1  # cup: allow-state-read nothing here reads State\n"
        "# cup: allow-plian a kind that does not exist\n"
        "TWO = 2\n")})
    assert found == ["add.py:1 CUP-I009", "add.py:4 CUP-I009", "add.py:5 CUP-I009"]
    first = out.get("findings")[0]
    assert first.severity == "warning"
    assert first.message.startswith("The comment `cup: allow-plain` allows nothing. Remove it")
    assert out.get("exit_code") == 0


def test_a_stale_comment_fails_a_strict_run(tmp_path):
    (tmp_path / "one.py").write_text("# cup: allow-plain no reason\nONE = 1\n")
    assert main(["--strict", str(tmp_path)]) == 1
    assert main(["--strict", "--disable", "CUP-I009", str(tmp_path)]) == 0


def test_a_comment_that_allows_a_finding_is_not_reported_and_a_string_is_not_a_comment(tmp_path):
    out, found = lint(tmp_path, {"pick.py": (
        "# cup: allow-plain the entry of the program\n"
        "def pick(items):\n    for each in items:\n        return each\n"
        "def choose(flag):  # cup: allow-plain a small helper\n    return 1 if flag else 2\n"
        '"""The marker ``# cup: allow-plain`` allows a finding."""\n'
        'HELP = "say why: # cup: allow-plain <reason>"\n'
        "# For plain logic, write cup: allow-plain and the reason.\n")})
    assert found == []
    assert len(out.get("suppressed")) == 2


def test_a_comment_for_a_rule_that_is_off_or_for_the_other_linter_is_not_reported(tmp_path):
    out, found = lint(tmp_path, {"pick.py": (
        "# cup: allow-plain the entry\ndef pick(flag):\n    return 1 if flag else 2\n"
        "STEP = 1  # cup: allow-anonymous the other linter reads this one\n")}, disable=["CUP-I008"])
    assert found == []
    assert out.get("suppressed") == []
