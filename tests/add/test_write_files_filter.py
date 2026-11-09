from codeupipe import Payload
from codeupipe_add.write_files_filter import WriteFilesFilter


def test_both_files_are_written_with_their_directories(tmp_path):
    out = WriteFilesFilter().call(Payload({"root": str(tmp_path), "component_path": "src/a/x_filter.py",
                                           "component_text": "c", "test_path": "tests/test_x_filter.py",
                                           "test_text": "t"}))
    assert out.get("written") == ["src/a/x_filter.py", "tests/test_x_filter.py"]
    assert (tmp_path / "src/a/x_filter.py").read_text() == "c"
    assert (tmp_path / "tests/test_x_filter.py").read_text() == "t"
