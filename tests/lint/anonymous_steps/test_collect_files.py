"""CollectFiles: paths -> Python source files."""

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


def _collect(paths):
    return CollectFiles().call(Payload({"paths": paths}))


def test_takes_python_files_and_skips_build_output_and_other_files():
    with tempfile.TemporaryDirectory() as root:
        expected = [_touch(root, "a/x.py"), _touch(root, "b/deep/y.py")]
        for skipped in ["node_modules/m/x.py", ".git/x.py", "build/x.py", "__pycache__/x.py", ".venv/x.py",
                        "dist/x.py", "notes.md", "c/x.go", "c/x.ts"]:
            _touch(root, skipped)
        out = _collect([root])
    assert out.get("files") == {"python": sorted(expected)}
    assert out.get("errors") == []


def test_explicit_file_is_taken_even_in_a_skipped_directory():
    with tempfile.TemporaryDirectory() as root:
        path = _touch(root, "build/x.py")
        out = _collect([path])
    assert out.get("files")["python"] == [path]


def test_exclude_globs_skip_matching_files():
    with tempfile.TemporaryDirectory() as root:
        keep = _touch(root, "src/x.py")
        _touch(root, "tests/fixtures/y.py")
        out = CollectFiles().call(Payload({"paths": [root], "exclude": ["*/fixtures/*"]}))
    assert out.get("files") == {"python": [keep]}


def test_missing_path_is_an_error():
    out = _collect(["/no/such/path/anywhere"])
    assert out.get("errors") == ["/no/such/path/anywhere: no such file or directory"]
