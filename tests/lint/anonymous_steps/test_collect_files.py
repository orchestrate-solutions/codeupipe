"""CollectFiles: paths -> source files grouped by language."""

import os
import tempfile

from codeupipe import Payload

from codeupipe_lint.anonymous_steps.collect_files import CollectFiles


def _touch(root, rel):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write("")
    return path


def _collect(paths, languages=None):
    data = {"paths": paths}
    if languages is not None:
        data["languages"] = languages
    return CollectFiles().call(Payload(data))


def test_groups_files_by_language_and_skips_build_output():
    with tempfile.TemporaryDirectory() as root:
        expected = {
            "python": [_touch(root, "a/x.py")],
            "go": [_touch(root, "b/x.go")],
            "ts": [_touch(root, "c/x.ts"), _touch(root, "c/y.tsx")],
            "rust": [_touch(root, "d/x.rs")],
            "cpp": [_touch(root, "e/x.cpp"), _touch(root, "e/x.hpp")],
            "kotlin": [_touch(root, "f/x.kt")],
            "csharp": [_touch(root, "g/x.cs")],
        }
        for skipped in ["node_modules/m/x.ts", ".git/x.py", "target/x.rs", "c/types.d.ts",
                        "bin/x.cs", "obj/x.cs", "build/x.kt", "__pycache__/x.py", ".venv/x.py", "dist/x.ts",
                        "notes.md"]:
            _touch(root, skipped)
        out = _collect([root])
    files = out.get("files")
    assert {lang: sorted(paths) for lang, paths in files.items() if paths} == {
        lang: sorted(paths) for lang, paths in expected.items()}
    assert out.get("errors") == []


def test_explicit_file_is_taken_even_in_a_skipped_directory():
    with tempfile.TemporaryDirectory() as root:
        path = _touch(root, "build/x.py")
        out = _collect([path])
    assert out.get("files")["python"] == [path]


def test_languages_restricts_the_result():
    with tempfile.TemporaryDirectory() as root:
        py = _touch(root, "x.py")
        _touch(root, "x.go")
        out = _collect([root], languages=["python"])
    assert out.get("files") == {"python": [py]}


def test_exclude_globs_skip_matching_files():
    with tempfile.TemporaryDirectory() as root:
        keep = _touch(root, "src/x.py")
        _touch(root, "tests/fixtures/y.py")
        out = CollectFiles().call(Payload({"paths": [root], "exclude": ["*/fixtures/*"]}))
    assert out.get("files") == {"python": [keep]}


def test_missing_path_is_an_error():
    out = _collect(["/no/such/path/anywhere"])
    assert out.get("errors") == ["/no/such/path/anywhere: no such file or directory"]
