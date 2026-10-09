"""cup.config.json: what Lint and Compile do when they are given no arguments.

    {"lint":    {"paths": ["src"], "exclude": ["*/generated/*"]},
     "compile": [{"target": "app.pipelines:checkout", "out": "build/checkout",
                  "lowering": "inline", "observe": false}]}

The file is optional and every key in it is optional. A key is here only
because a tool reads it: one that no tool reads is an error, not ignored, so
the file cannot fill up with settings that do nothing. An argument given on
the command line wins over the file.
"""

import json
import os
from typing import Optional

__all__ = ["ConfigError", "DEFAULT_NAME", "load_config"]

DEFAULT_NAME = "cup.config.json"
_SECTIONS = ("lint", "compile")
_LINT_KEYS = ("paths", "exclude")
_PIPELINE_KEYS = ("target", "out", "lowering", "observe")
_LOWERINGS = ("steps", "inline")


class ConfigError(Exception):
    """The config file cannot be used as it is."""


def _unknown(where: str, given, allowed) -> None:
    extra = sorted(set(given) - set(allowed))
    if extra:
        raise ConfigError("%s: unknown key %s (the keys are %s)" % (
            where, ", ".join(repr(key) for key in extra), ", ".join(allowed)))


def _strings(where: str, value) -> None:
    if not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
        raise ConfigError("%s must be a list of strings" % where)


def load_config(path: Optional[str] = None) -> Optional[dict]:
    """The config as a dict, checked. With no ``path``: ``cup.config.json`` in
    the working directory, or None when there is no such file."""
    name = path or DEFAULT_NAME
    if not os.path.isfile(name):
        if path is None:
            return None
        raise ConfigError("%s: no such file" % name)
    try:
        with open(name, encoding="utf-8") as handle:
            config = json.load(handle)
    except ValueError as error:
        raise ConfigError("%s is not valid JSON: %s" % (name, error))
    if not isinstance(config, dict):
        raise ConfigError("%s must hold a JSON object" % name)
    _unknown(name, config, _SECTIONS)

    lint = config.get("lint", {})
    if not isinstance(lint, dict):
        raise ConfigError("%s: lint must be an object" % name)
    _unknown("%s: lint" % name, lint, _LINT_KEYS)
    for key in lint:
        _strings("%s: lint.%s" % (name, key), lint[key])

    pipelines = config.get("compile", [])
    if not isinstance(pipelines, list):
        raise ConfigError("%s: compile must be a list of pipelines" % name)
    for index, pipeline in enumerate(pipelines):
        where = "%s: compile[%d]" % (name, index)
        if not isinstance(pipeline, dict):
            raise ConfigError("%s must be an object" % where)
        _unknown(where, pipeline, _PIPELINE_KEYS)
        for key in ("target", "out"):
            if not isinstance(pipeline.get(key), str):
                raise ConfigError("%s needs %s, a string" % (where, key))
        if pipeline.get("lowering", "steps") not in _LOWERINGS:
            raise ConfigError("%s: lowering is one of %s" % (where, ", ".join(_LOWERINGS)))
        if not isinstance(pipeline.get("observe", False), bool):
            raise ConfigError("%s: observe is true or false" % where)
        if pipeline.get("observe") and pipeline.get("lowering") == "inline":
            raise ConfigError("%s: observe needs the steps lowering, not inline" % where)
    return config
