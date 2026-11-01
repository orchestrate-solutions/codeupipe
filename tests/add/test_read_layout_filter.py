import sys

import pytest

from codeupipe import Payload
from codeupipe_add.read_layout_filter import ReadLayoutFilter
from codeupipe_add.refusal import Refusal


def read(root, name):
    return ReadLayoutFilter().call(Payload({"root": str(root), "layout_path": name})).get("layout")


def test_a_layout_in_json_is_read_with_the_standard_library(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    (tmp_path / "cup.layout.json").write_text('{"lang": "python", "components": []}')
    assert read(tmp_path, "cup.layout.json") == {"lang": "python", "components": []}


def test_a_layout_in_yaml_is_read(tmp_path):
    (tmp_path / "cup.layout.yaml").write_text("lang: python\ncomponents:\n  - kind: filter\n    name: Discount\n")
    assert read(tmp_path, "cup.layout.yaml") == {"lang": "python",
                                                 "components": [{"kind": "filter", "name": "Discount"}]}


def test_a_yaml_layout_with_no_yaml_reader_says_what_to_install(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    (tmp_path / "cup.layout.yaml").write_text("lang: python\n")
    with pytest.raises(Refusal) as refused:
        read(tmp_path, "cup.layout.yaml")
    assert refused.value.exit_code == 2 and "codeupipe-add[layout]" in str(refused.value)


@pytest.mark.parametrize("text, wanted", [
    (None, "cannot be read"),
    ("- kind: filter\n", "mapping"),
    ("lang: [python\n", "cannot be read"),
    ("lang: python\ncomponents:\n  - kind: filter\n    name: A\n    description: One.\n    description: Two.\n",
     "description two times"),
    ('{"lang": "python", "lang": "go"}', "lang two times"),
])
def test_a_file_that_cannot_be_read_or_is_not_a_mapping_is_refused(tmp_path, text, wanted):
    if text is not None:
        (tmp_path / "cup.layout.yaml").write_text(text)
    with pytest.raises(Refusal) as refused:
        read(tmp_path, "cup.layout.yaml")
    assert refused.value.exit_code == 2 and wanted in str(refused.value)
