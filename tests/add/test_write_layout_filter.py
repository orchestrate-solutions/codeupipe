from codeupipe import Payload
from codeupipe_add.write_layout_filter import WriteLayoutFilter


def component(name):
    return {"component_path": "app/%s.py" % name, "component_text": "# %s\n" % name,
            "test_path": "tests/test_%s.py" % name, "test_text": "# test %s\n" % name}


def write(root, *components):
    out = WriteLayoutFilter().call(Payload({"root": str(root), "components": list(components)}))
    return out.get("written"), out.get("kept")


def test_each_file_is_written_in_order_component_first(tmp_path):
    written, kept = write(tmp_path, component("a"), component("b"))
    assert written == ["app/a.py", "tests/test_a.py", "app/b.py", "tests/test_b.py"] and kept == []
    assert (tmp_path / "app" / "b.py").read_text() == "# b\n"


def test_a_file_that_exists_is_kept_by_itself_and_the_others_are_written(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_text("mine\n")
    written, kept = write(tmp_path, component("a"))
    assert written == ["tests/test_a.py"] and kept == ["app/a.py"]
    assert (tmp_path / "app" / "a.py").read_text() == "mine\n"
