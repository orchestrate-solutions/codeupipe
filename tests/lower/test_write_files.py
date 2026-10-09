"""Unit tests for WriteFilesTap (M1)."""

from pathlib import Path

from codeupipe import Payload
from codeupipe.lower.taps.write_files import WriteFilesTap


class TestWriteFilesTap:
    def test_writes_files_under_output_dir(self, tmp_path):
        tap = WriteFilesTap()
        tap.observe(Payload({
            "output_dir": str(tmp_path),
            "files": [
                {"path": "src/steps/clean.py", "content": "def clean(data):\n    return data\n"},
                {"path": "src/steps/pipeline.py", "content": "def run(data):\n    return data\n"},
            ],
        }))
        assert (tmp_path / "src/steps/clean.py").read_text() == "def clean(data):\n    return data\n"
        assert (tmp_path / "src/steps/pipeline.py").exists()

    def test_dry_run_writes_nothing(self, tmp_path):
        tap = WriteFilesTap()
        tap.observe(Payload({
            "output_dir": str(tmp_path),
            "dry_run": True,
            "files": [
                {"path": "src/steps/clean.py", "content": "def clean(data):\n    return data\n"},
            ],
        }))
        assert not (tmp_path / "src/steps/clean.py").exists()

    def test_missing_files_is_a_no_op(self, tmp_path):
        tap = WriteFilesTap()
        tap.observe(Payload({"output_dir": str(tmp_path)}))
        assert list(tmp_path.iterdir()) == []
