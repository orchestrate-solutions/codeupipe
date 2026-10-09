"""
Tests for State (Pipeline Execution Metadata)

Testing the State class that tracks pipeline execution.
"""

import pytest
from codeupipe.core.state import State


class TestState:
    """Test the State execution metadata tracker."""

    @pytest.mark.unit
    @pytest.mark.core
    def test_initial_state(self):
        """Test that State starts empty."""
        state = State()
        assert state.executed == []
        assert state.skipped == []
        assert state.errors == []
        assert state.timings == {}

    @pytest.mark.unit
    @pytest.mark.core
    def test_mark_executed(self):
        """Test marking filters as executed."""
        state = State()
        state.mark_executed("filter_a")
        state.mark_executed("filter_b")
        assert state.executed == ["filter_a", "filter_b"]

    @pytest.mark.unit
    @pytest.mark.core
    def test_mark_skipped(self):
        """Test marking filters as skipped."""
        state = State()
        state.mark_skipped("gated_filter")
        assert state.skipped == ["gated_filter"]

    @pytest.mark.unit
    @pytest.mark.core
    def test_record_error(self):
        """Test recording errors."""
        state = State()
        err = ValueError("something broke")
        state.record_error("bad_filter", err)

        assert len(state.errors) == 1
        assert state.errors[0] == ("bad_filter", err)

    @pytest.mark.unit
    @pytest.mark.core
    def test_repr(self):
        """Test string representation."""
        state = State()
        state.mark_executed("a")
        state.mark_skipped("b")
        repr_str = repr(state)
        assert "State" in repr_str
        assert "a" in repr_str
        assert "b" in repr_str
