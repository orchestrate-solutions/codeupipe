"""
EmitOrchestratorFilter — the ``def run(data): ...`` glue.

Direction: export (CUP -> standard Python).
Milestone: M1.

Two forms, chosen by the export payload's ``observe`` flag:

* fast (default): ``run(data)`` calls each step in order. Same output as
  the dynamic run, no State, no Hooks.
* observable (``observe=True``): ``run(data, state=None, hooks=None,
  timing=False, trace_id=None)`` also records State into the ``state`` dict
  and calls Hooks, in exactly the order the dynamic ``Pipeline.run`` does
  (conformance/API.md, "Hook" and "State"). A nested pipeline's steps are
  run inline but reported as the one step that nested them.
"""

from __future__ import annotations

import os
from itertools import groupby
from typing import List

from codeupipe.core import Payload


__all__ = ["EmitOrchestratorFilter"]

def _default_config(payload: Payload):
    return payload.get("config") or {
        "pattern": payload.get("pattern", "flat"),
        "output": {"base": "src/", "step": "steps/"},
    }


def _observed_step(name: str, body: List[str], pad: str) -> List[str]:
    """A Plane A step: hooks around it, timing, the failing-step marker."""
    return [
        f"{pad}_step = {name!r}",
        f"{pad}if timing:",
        f"{pad}    _t0 = _clock()",
        f"{pad}for _hook in hooks:",
        f"{pad}    _hook.before({name!r}, data)",
        *body,
        f"{pad}for _hook in hooks:",
        f"{pad}    _hook.after({name!r}, data)",
        f"{pad}if timing:",
        f"{pad}    timings[{name!r}] = _clock() - _t0",
    ]


class EmitOrchestratorFilter:
    """Emit the top-level orchestrator that calls each step in order."""

    def call(self, payload: Payload) -> Payload:
        pipeline_ir = payload.get("pipeline_ir")
        config = _default_config(payload)
        output = config.get("output", {})
        base = output.get("base", "src/")
        step_dir = output.get("step", "steps/")
        files = list(payload.get("files") or [])

        lines = EmitOrchestratorFilter._import_lines(pipeline_ir.steps)
        if payload.get("observe"):
            lines.extend(["", ""] + EmitOrchestratorFilter._observed_run(pipeline_ir.steps, payload.get("source_hooks") or ()))
        else:
            lines.extend(["", ""] + EmitOrchestratorFilter._fast_run(pipeline_ir.steps))
        lines.append("")

        files.append({
            "path": os.path.join(base, step_dir, "pipeline.py"),
            "content": "\n".join(lines),
        })
        files.append({
            "path": os.path.join(base, step_dir, "__init__.py"),
            "content": "from .pipeline import run\n\n__all__ = [\"run\"]\n",
        })
        return payload.insert("files", files)

    @staticmethod
    def _import_lines(steps) -> List[str]:
        # Each step lives in its own sibling module, so the orchestrator must
        # import it. Relative imports keep step names (``json``, ``truncate``)
        # from shadowing top-level modules on the customer's sys.path.
        # Code uses each step's generated identifier (``step_03_validate``), never
        # its label, reported in State and to Hooks.
        lines = []
        for step in steps:
            names = [step.ident]
            if step.kind == "valve":
                names.append(f"{step.ident}_predicate")
            lines.append(f"from .{step.ident} import {', '.join(names)}")
        return lines

    @staticmethod
    def _plain_lines(step, pad: str, var: str = "data") -> List[str]:
        """One step, no bookkeeping: the fast form, and a nested pipeline's body
        (which works on its own variable, ``var``)."""
        fn = step.ident
        if step.kind == "valve":
            return [f"{pad}if {fn}_predicate({var}):", f"{pad}    {var} = {fn}({var})"]
        if step.kind == "tap":
            # Plane B: a Tap failure never halts the run, matching the dynamic
            # runtime. Exception only; KeyboardInterrupt etc. pass.
            return [f"{pad}try:", f"{pad}    {fn}({var})", f"{pad}except Exception:", f"{pad}    pass"]
        return [f"{pad}{var} = {fn}({var})"]

    @staticmethod
    def _fast_run(steps) -> List[str]:
        # Steps write in place, so run() works on its own copy of the caller's dict.
        lines = ["def run(data):", "    data = dict(data)"]
        for step in steps:
            lines.extend(EmitOrchestratorFilter._plain_lines(step, "    "))
        lines.append("    return data")
        return lines

    @staticmethod
    def _observed_run(steps, source_hooks) -> List[str]:
        pad = "        "
        body: List[str] = []
        for group, members in groupby(steps, key=lambda s: s.group):
            members = list(members)
            if group is not None:
                # A nested pipeline: one step in this run's State and Hooks. Its
                # own skips and Tap errors belong to its run, as dynamically.
                # It works on its own copy, as the nested run does: if it fails, the outer on_error hooks see ``data`` as
                # it was when the nested pipeline was entered, as dynamically.
                inner = [line for step in members for line in EmitOrchestratorFilter._plain_lines(step, pad, "_nested")]
                body.extend(_observed_step(group, [f"{pad}_nested = dict(data)", *inner, f"{pad}data = _nested",
                                                   f"{pad}executed.append({group!r})"], pad))
                continue
            for step in members:
                name, fn = step.name, step.ident
                if step.kind == "tap":
                    body.extend([
                        f"{pad}_step = None",
                        f"{pad}try:",
                        f"{pad}    {fn}(data)",
                        f"{pad}except Exception as _error:",
                        f"{pad}    errors.append(({name!r}, _error))",
                        f"{pad}executed.append({name!r})",
                    ])
                elif step.kind == "valve":
                    body.extend(_observed_step(name, [
                        f"{pad}if {fn}_predicate(data):",
                        f"{pad}    data = {fn}(data)",
                        f"{pad}    executed.append({name!r})",
                        f"{pad}else:",
                        f"{pad}    skipped.append({name!r})",
                    ], pad))
                else:
                    body.extend(_observed_step(name, [
                        f"{pad}data = {fn}(data)",
                        f"{pad}executed.append({name!r})",
                    ], pad))
        return [
            "from time import perf_counter as _clock",
            "",
            f"SOURCE_HOOKS = {tuple(source_hooks)!r}",
            "",
            "",
            "def run(data, state=None, hooks=None, timing=False, trace_id=None):",
            '    """Run the pipeline, recording State into ``state`` and calling ``hooks``.',
            "",
            "    state: a dict to fill with executed, skipped, errors [(name, error)],",
            "        timings {name: seconds} (only when ``timing``) and trace_id.",
            "    hooks: objects with before(step, data), after(step, data) and",
            "        on_error(step, error, data); step is None for the pipeline itself.",
            '    """',
            "    if hooks is None:",
            "        if SOURCE_HOOKS:",
            "            raise TypeError(",
            '                "this pipeline was exported with Hooks (" + ", ".join(SOURCE_HOOKS) + "): "',
            '                "pass them as run(..., hooks=[...]), or hooks=() to run without them")',
            "        hooks = ()",
            "    if state is None:",
            "        state = {}",
            '    executed = state["executed"] = []',
            '    skipped = state["skipped"] = []',
            '    errors = state["errors"] = []',
            '    timings = state["timings"] = {}',
            '    state["trace_id"] = trace_id',
            "    _step = None",
            "    _t0 = 0.0",
            "    data = dict(data)",
            "    for _hook in hooks:",
            "        _hook.before(None, data)",
            "    try:",
            *(body or [f"{pad}pass"]),
            "    except Exception as _error:",
            "        if _step is not None:",
            "            if timing:",
            "                timings[_step] = _clock() - _t0",
            "            for _hook in hooks:",
            "                _hook.on_error(_step, _error, data)",
            "        for _hook in hooks:",
            "            _hook.on_error(None, _error, data)",
            "        raise",
            "    for _hook in hooks:",
            "        _hook.after(None, data)",
            "    return data",
        ]
