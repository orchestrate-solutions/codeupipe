"""cup.config.json: what Lint and Compile do when they are given no arguments."""

import json

import pytest

from codeupipe.config import ConfigError, load_config
from codeupipe.lower.__main__ import main as compile_main
from codeupipe_lint.anonymous_steps.__main__ import main as anonymous_main
from codeupipe_lint.invariants.__main__ import main as invariants_main

TARGETS = "tests.lower.fixtures.cli_targets"


def write(directory, config, name="cup.config.json"):
    (directory / name).write_text(json.dumps(config))
    return directory / name


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A directory with one clean file and one that breaks an invariant."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "clean_filter.py").write_text(
        "class CleanFilter:\n    def call(self, payload):\n        return payload.insert('a', 1)\n")
    (tmp_path / "src" / "generated").mkdir()
    (tmp_path / "src" / "generated" / "bad_filter.py").write_text(
        "class BadFilter:\n    def call(self, payload):\n        payload._data['a'] = 1\n        return payload\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


# -- the file ---------------------------------------------------------------------

def test_no_file_is_no_config(project):
    assert load_config() is None


def test_reads_the_sections(project):
    write(project, {"lint": {"paths": ["src"], "exclude": ["*/generated/*"]},
                    "compile": [{"target": "app:build", "out": "build/app", "lowering": "inline", "observe": False}]})

    assert load_config() == {"lint": {"paths": ["src"], "exclude": ["*/generated/*"]},
                             "compile": [{"target": "app:build", "out": "build/app", "lowering": "inline",
                                          "observe": False}]}


def test_a_named_file_that_does_not_exist_is_an_error(project):
    with pytest.raises(ConfigError) as error:
        load_config("other.json")
    assert "other.json" in str(error.value)


def test_a_file_that_is_not_json_is_an_error(project):
    (project / "cup.config.json").write_text("{not json")
    with pytest.raises(ConfigError) as error:
        load_config()
    assert "cup.config.json" in str(error.value)


@pytest.mark.parametrize("config, names", [
    ({"test": {}}, ["test", "lint", "compile"]),
    ({"lint": {"path": ["src"]}}, ["path", "paths", "exclude"]),
    ({"compile": [{"target": "a:b", "out": "o", "mode": "inline"}]}, ["mode", "lowering"]),
])
def test_a_key_no_tool_reads_is_an_error_that_names_the_keys_there_are(project, config, names):
    write(project, config)
    with pytest.raises(ConfigError) as error:
        load_config()
    assert all(name in str(error.value) for name in names)


@pytest.mark.parametrize("config, says", [
    ({"lint": {"paths": "src"}}, "paths"),
    ({"compile": {"target": "a:b"}}, "compile"),
    ({"compile": [{"out": "o"}]}, "target"),
    ({"compile": [{"target": "a:b"}]}, "out"),
    ({"compile": [{"target": "a:b", "out": "o", "lowering": "fast"}]}, "lowering"),
    ({"compile": [{"target": "a:b", "out": "o", "lowering": "inline", "observe": True}]}, "observe"),
])
def test_a_wrong_value_is_an_error(project, config, says):
    write(project, config)
    with pytest.raises(ConfigError) as error:
        load_config()
    assert says in str(error.value)


# -- lint ---------------------------------------------------------------------------

def test_lint_with_no_arguments_uses_the_config(project, capsys):
    write(project, {"lint": {"paths": ["src"], "exclude": ["*/generated/*"]}})

    assert invariants_main([]) == 0
    assert "No invariant violations" in capsys.readouterr().out
    assert anonymous_main([]) == 0


def test_lint_finds_what_the_config_does_not_exclude(project, capsys):
    write(project, {"lint": {"paths": ["src"]}})

    assert invariants_main([]) == 1
    assert "CUP-I001" in capsys.readouterr().out


def test_paths_on_the_command_line_win_over_the_config(project, capsys):
    write(project, {"lint": {"paths": ["src/generated"]}})

    assert invariants_main(["src/clean_filter.py"]) == 0


def test_a_path_named_on_the_command_line_is_checked_even_if_the_config_excludes_it(project, capsys):
    write(project, {"lint": {"paths": ["src"], "exclude": ["*/generated/*"]}})

    assert invariants_main(["src/generated/bad_filter.py"]) == 1
    assert "CUP-I001" in capsys.readouterr().out
    assert anonymous_main(["src/generated/bad_filter.py"]) == 0     # checked, and it has no anonymous step


def test_with_paths_on_the_command_line_a_broken_config_does_not_matter(project):
    write(project, {"lint": {"path": ["src"]}})

    assert invariants_main(["src/clean_filter.py"]) == 0


def test_an_exclude_on_the_command_line_wins_over_the_config(project):
    write(project, {"lint": {"paths": ["src"], "exclude": ["*/generated/*"]}})

    assert invariants_main(["--exclude", "*/nothing/*"]) == 1


def test_lint_with_no_arguments_and_no_config_is_a_usage_error(project):
    with pytest.raises(SystemExit) as stop:
        invariants_main([])
    assert stop.value.code == 2


def test_a_bad_config_stops_lint_with_exit_2(project, capsys):
    write(project, {"lint": {"path": ["src"]}})

    assert invariants_main([]) == 2
    assert "path" in capsys.readouterr().err


def test_lint_reads_a_named_config(project):
    write(project, {"lint": {"paths": ["src/clean_filter.py"]}}, "ci.json")

    assert invariants_main(["--config", "ci.json"]) == 0


# -- compile ------------------------------------------------------------------------

def test_compile_with_no_arguments_exports_every_pipeline_in_the_config(project, capsys):
    write(project, {"compile": [
        {"target": f"{TARGETS}:build_pricing", "out": "build/pricing"},
        {"target": f"{TARGETS}:PRICING", "out": "build/inline", "lowering": "inline"},
    ]})

    assert compile_main([]) == 0
    assert (project / "build" / "pricing" / "src" / "steps" / "pipeline.py").is_file()
    assert sorted(p.name for p in (project / "build" / "inline" / "src" / "steps").iterdir()) == [
        "__init__.py", "pipeline.py"]


def test_compile_observe_comes_from_the_config(project):
    write(project, {"compile": [{"target": f"{TARGETS}:build_pricing", "out": "build/observed", "observe": True}]})

    assert compile_main([]) == 0
    assert "state" in (project / "build" / "observed" / "src" / "steps" / "pipeline.py").read_text()


def test_one_refused_pipeline_gives_exit_1_and_the_others_are_still_exported(project, capsys):
    write(project, {"compile": [
        {"target": f"{TARGETS}:REFUSED", "out": "build/refused"},
        {"target": f"{TARGETS}:build_pricing", "out": "build/pricing"},
    ]})

    assert compile_main([]) == 1
    assert "HoldsAnObject" in capsys.readouterr().err
    assert not (project / "build" / "refused").exists()
    assert (project / "build" / "pricing" / "src" / "steps" / "pipeline.py").is_file()


def test_a_target_on_the_command_line_ignores_the_config(project):
    write(project, {"compile": [{"target": f"{TARGETS}:REFUSED", "out": "build/refused"}]})

    assert compile_main([f"{TARGETS}:build_pricing", "--out", "build/one"]) == 0
    assert not (project / "build" / "refused").exists()


def test_a_target_on_the_command_line_still_needs_out(project, capsys):
    assert compile_main([f"{TARGETS}:build_pricing"]) == 2
    assert "--out" in capsys.readouterr().err


def test_compile_with_no_arguments_and_nothing_to_export_is_a_usage_error(project, capsys):
    assert compile_main([]) == 2
    write(project, {"lint": {"paths": ["src"]}})
    assert compile_main([]) == 2
    assert "cup.config.json" in capsys.readouterr().err


def test_a_bad_config_stops_compile_with_exit_2(project, capsys):
    write(project, {"compile": [{"target": "a:b"}]})

    assert compile_main([]) == 2
    assert "out" in capsys.readouterr().err


# --- lint.disable: switch a rule off for the whole project -------------------

def test_a_disabled_rule_is_not_reported(project, capsys):
    write(project, {"lint": {"paths": ["src"], "disable": ["CUP-I001"]}})
    assert invariants_main([]) == 0
    assert "No invariant violations." in capsys.readouterr().out


def test_disable_on_the_command_line(project, capsys):
    assert invariants_main(["src"]) == 1
    capsys.readouterr()
    assert invariants_main(["--disable", "CUP-I001", "src"]) == 0


def test_disable_on_the_command_line_wins_over_the_config(project):
    write(project, {"lint": {"paths": ["src"], "disable": ["CUP-I001"]}})
    assert invariants_main(["--disable", "CUP-I002"]) == 1


def test_a_rule_of_the_other_linter_can_be_listed(project):
    write(project, {"lint": {"paths": ["src"], "disable": ["CUP-A001", "CUP-I001"]}})
    assert invariants_main([]) == 0
    assert anonymous_main([]) == 0


def test_disable_works_in_the_anonymous_step_linter(project, capsys):
    (project / "src" / "lam.py").write_text(
        "from codeupipe import Pipeline\n\np = Pipeline()\np.add_filter(lambda payload: payload)\n")
    assert anonymous_main(["src"]) == 1
    capsys.readouterr()
    assert anonymous_main(["--disable", "CUP-A001", "src"]) == 0


@pytest.mark.parametrize("main", [invariants_main, anonymous_main])
def test_a_rule_id_that_does_not_exist_is_an_error(project, capsys, main):
    assert main(["--disable", "CUP-I999", "src"]) == 2
    assert "CUP-I999" in capsys.readouterr().err


def test_disable_must_be_a_list_of_strings(project):
    write(project, {"lint": {"paths": ["src"], "disable": "CUP-I001"}})
    with pytest.raises(ConfigError, match="disable"):
        load_config()
