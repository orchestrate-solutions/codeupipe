"""Contract tests for UnsupportedFilterShape."""

import pytest

from codeupipe.lower.errors import UnsupportedFilterShape


class TestUnsupportedFilterShape:
    def test_is_an_exception(self):
        err = UnsupportedFilterShape(
            filter_name="X",
            method_name="call",
            line=1,
            col=0,
            node_kind="Attribute",
            suggestion="Use a literal string key.",
        )
        assert isinstance(err, Exception)

    def test_str_includes_all_fields(self):
        err = UnsupportedFilterShape(
            filter_name="MyFilter",
            method_name="call",
            line=42,
            col=8,
            node_kind="Name",
            suggestion="Inline the constant.",
        )
        s = str(err)
        assert "MyFilter" in s
        assert "call" in s
        assert "42" in s
        assert "Name" in s
        assert "Inline the constant." in s

    def test_can_be_raised_and_caught(self):
        with pytest.raises(UnsupportedFilterShape) as info:
            raise UnsupportedFilterShape(
                filter_name="X",
                method_name="call",
                line=1,
                col=0,
                node_kind="Attribute",
                suggestion="hint",
            )
        assert info.value.line == 1
