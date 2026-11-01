import pytest

from codeupipe import Payload
from codeupipe_add.refusal import Refusal
from codeupipe_add.refuse_existing_filter import RefuseExistingFilter


def check(root):
    RefuseExistingFilter().call(Payload({"root": str(root), "component_path": "discount_filter.py",
                                         "test_path": "tests/test_discount_filter.py"}))


def test_no_file_there_goes_on(tmp_path):
    check(tmp_path)


def test_each_file_that_exists_is_named_and_the_exit_code_is_1(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "discount_filter.py").write_text("")
    (tmp_path / "tests" / "test_discount_filter.py").write_text("")
    with pytest.raises(Refusal) as refused:
        check(tmp_path)
    assert refused.value.exit_code == 1
    assert str(refused.value) == "discount_filter.py exists\ntests/test_discount_filter.py exists"
