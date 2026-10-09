from scorecard.strict import first_difference, strict_equal


def test_equal_structures():
    assert strict_equal({"a": [1, {"b": None}]}, {"a": [1, {"b": None}]})


def test_bool_is_not_int_is_not_float():
    assert not strict_equal({"a": True}, {"a": 1})
    assert not strict_equal({"a": 1}, {"a": 1.0})


def test_key_order_counts():
    assert "key order" in first_difference({"a": 1, "b": 2}, {"b": 2, "a": 1})


def test_reports_path_of_first_difference():
    assert first_difference({"a": [1, 2]}, {"a": [1, 3]}).startswith("$['a'][1]")


def test_length_and_type():
    assert "length" in first_difference([1], [1, 2])
    assert "type" in first_difference(None, {})
