"""build_lint_pipeline / lint_paths: the linter is itself a CUP pipeline."""

from codeupipe_lint.anonymous_steps.lint_pipeline import build_lint_pipeline, lint_paths

from ._support import fixture


def test_the_linter_is_a_pipeline_of_named_filters():
    identities = build_lint_pipeline().identities
    assert identities[0] == "codeupipe_lint.anonymous_steps.collect_files.CollectFiles"
    assert "codeupipe_lint.anonymous_steps.analyze_python.AnalyzePython" in identities
    assert identities[-2:] == ["codeupipe_lint.anonymous_steps.apply_suppressions.ApplySuppressions",
                               "codeupipe_lint.anonymous_steps.format_report.FormatReport"]


def test_lint_paths_reports_and_sets_the_exit_code():
    out = lint_paths([fixture("python", "probe.py")])
    assert [f.rule for f in out.get("findings")] == ["CUP-A001", "CUP-A002", "CUP-A003"]
    assert out.get("exit_code") == 1
    assert out.get("report").endswith("3 anonymous steps.")


def test_lint_paths_clean():
    out = lint_paths([fixture("python", "negative.py")])
    assert out.get("findings") == [] and out.get("exit_code") == 0


def test_every_language_in_one_run():
    out = lint_paths([fixture(lang, name) for lang, name in [
        ("python", "probe.py"), ("go", "probe.go"), ("ts", "probe.ts"), ("rust", "probe.rs"),
        ("cpp", "probe.cpp"), ("kotlin", "Probe.kt"), ("csharp", "Probe.cs")]])
    langs = {f.lang for f in out.get("findings")}
    if out.get("errors"):  # a toolchain is missing on this machine: the run says so
        assert out.get("exit_code") == 2
    else:
        assert langs == {"python", "go", "ts", "rust", "cpp", "kotlin", "csharp"}


def test_suppression_comment_in_a_c_family_language():
    import os
    import tempfile
    source = ("fn main() {\n"
              "    let p = Pipeline::new()\n"
              "        .add_filter(Box::new(|p| p), \"a\") // cup: allow-anonymous (a test double)\n"
              "        .add_filter(Box::new(|p| p), \"b\");\n"
              "}\n")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "x.rs")
        with open(path, "w") as handle:
            handle.write(source)
        out = lint_paths([path])
    assert [f.line for f in out.get("findings")] == [4]
    assert [f.line for f in out.get("suppressed")] == [3]
