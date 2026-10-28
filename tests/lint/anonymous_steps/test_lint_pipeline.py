"""build_lint_pipeline / lint_paths: the linter is itself a CUP pipeline."""

from codeupipe_lint.anonymous_steps.lint_pipeline import build_lint_pipeline, lint_paths

from ._support import fixture


def test_the_linter_is_a_pipeline_of_named_filters():
    labels = build_lint_pipeline().labels
    assert labels[0] == "CollectFilesFilter"
    assert "AnalyzePythonFilter" in labels
    assert labels[-2:] == ["ApplySuppressionsFilter",
                               "FormatReportFilter"]


def test_lint_paths_reports_and_sets_the_exit_code():
    out = lint_paths([fixture("python", "probe.py")])
    assert [f.rule for f in out.get("findings")] == ["CUP-A001", "CUP-A002", "CUP-A003"]
    assert out.get("exit_code") == 1
    assert out.get("report").endswith("3 anonymous steps.")


def test_lint_paths_clean():
    out = lint_paths([fixture("python", "negative.py")])
    assert out.get("findings") == [] and out.get("exit_code") == 0


def test_suppression_comment_drops_only_its_own_line(tmp_path):
    source = "\n".join([
        "from codeupipe import Pipeline",
        "",
        "p = Pipeline()",
        "p.add_filter(lambda payload: payload)  # cup: allow-anonymous (a test double)",
        "p.add_filter(lambda payload: payload)",
        "",
    ])
    path = tmp_path / "x.py"
    path.write_text(source)
    out = lint_paths([str(path)])
    assert [f.line for f in out.get("findings")] == [5]
    assert [f.line for f in out.get("suppressed")] == [4]
