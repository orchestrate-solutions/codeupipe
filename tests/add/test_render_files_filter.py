import ast

import pytest

from codeupipe import Payload
from codeupipe_add.render_files_filter import RenderFilesFilter
from codeupipe_add.templates import COMPONENTS


def render(kind, description=""):
    return RenderFilesFilter().call(Payload({"kind": kind, "type_name": "XFilter", "snake": "x_filter",
                                             "module": "src.x_filter", "description": description}))


@pytest.mark.parametrize("kind", sorted(COMPONENTS))
def test_each_kind_gives_python_that_parses(kind):
    out = render(kind)
    ast.parse(out.get("component_text"))
    ast.parse(out.get("test_text"))


def test_the_header_has_the_description_or_a_todo():
    assert render("filter", "Takes a rate off the price.").get("component_text").startswith(
        '"""XFilter: Takes a rate off the price."""')
    assert "TODO: say what XFilter does." in render("filter").get("component_text")


def test_a_description_cannot_end_the_docstring_early():
    text = render("filter", 'Ends with """ and a \\ here').get("component_text")
    assert ast.get_docstring(ast.parse(text)) == 'XFilter: Ends with """ and a \\ here'


def test_the_test_imports_the_component_and_fails_on_purpose():
    text = render("filter").get("test_text")
    assert "from src.x_filter import XFilter" in text
    assert 'raise AssertionError("Write the acceptance case for XFilter.")' in text
