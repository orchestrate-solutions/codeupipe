"""RunCompiledFilter: run the case as compiled code."""

import copy

import conformance_sink as sink
from codeupipe import Payload


class RunCompiledFilter:
    """Filter (sync).

    Input keys: ``case``, ``package`` (from ExportFilter), ``observe``,
    ``hooks``.
    Output keys: ``result``: ``output`` or ``error``, and ``input_after``.
    With ``observe`` also ``state``, ``inner_states`` and, for a case that
    asks for them, ``hooks``. Compiled code is a function, so it has no
    ``pipeline_state``. The steps in the result are labels: NameStepsFilter
    gives them the names of the case.
    """

    def call(self, payload: Payload) -> Payload:
        case, package, observe = payload.get("case"), payload.get("package"), payload.get("observe")
        hooks = payload.get("hooks")
        data = copy.deepcopy(case["input"])
        result = {}
        state = {}
        inner_states = []

        def again(inner):
            # The compiled form is a function. To run the pipeline again is to call that function again,
            # and the caller gives each call its own State.
            if not observe:
                return package.run(inner)
            inner_states.append({})
            return package.run(inner, state=inner_states[-1], hooks=None)

        sink.RUN_AGAIN[0] = again
        try:
            if observe:
                result["output"] = package.run(data, state=state, hooks=hooks)
            else:
                result["output"] = package.run(data)
        except Exception as error:  # noqa: BLE001
            result["error"] = f"{type(error).__name__}: {error}"
        if observe:
            result["state"] = self.report(state)
            result["inner_states"] = [self.report(one) for one in inner_states]
            if case.get("hooks"):
                result["hooks"] = list(sink.HOOKS)
        result["input_after"] = data
        return payload.insert("result", result)

    def report(self, state) -> dict:
        return {"executed": list(state["executed"]), "skipped": list(state["skipped"]),
                "errors": [step for step, _error in state["errors"]]}
