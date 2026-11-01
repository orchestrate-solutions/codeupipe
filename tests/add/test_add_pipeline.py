import os

from codeupipe_add.__main__ import main


def test_the_command_prints_what_it_made_and_then_refuses_to_write_it_again(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["filter", "Discount", "--description", "Takes a rate off the price."]) == 0
    assert capsys.readouterr().out.splitlines() == ["discount_filter.py", "tests/test_discount_filter.py"]
    assert main(["filter", "Discount"]) == 1
    assert "discount_filter.py exists" in capsys.readouterr().err
    assert sorted(os.listdir(tmp_path)) == ["discount_filter.py", "tests"]
