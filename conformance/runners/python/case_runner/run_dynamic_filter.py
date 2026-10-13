"""RunDynamicFilter: run the case with ``Pipeline.run`` or ``Pipeline.run_async``."""

import asyncio
import copy

import conformance_sink as sink
from codeupipe import Payload, State


class RunDynamicFilter:
    """Filter (sync).

    Input keys: ``case``, ``pipeline``, ``run_async``, ``hooks``.
    Output keys: ``result``: ``output`` or ``error``, ``state`` (the State of
    the run), ``pipeline_state`` (``state`` on the Pipeline after the run),
    ``inner_states`` (the State of each run that a run_again step started),
    ``hooks`` for a case that asks for them, and ``input_after``. The steps
    in it are labels: NameStepsFilter gives them the names of the case.
    """

    def call(self, payload: Payload) -> Payload:
        case, pipeline, run_async = payload.get("case"), payload.get("pipeline"), payload.get("run_async")
        data = copy.deepcopy(case["input"])
        # With "given_state", the caller gives the State of the run. If not, the run makes one.
        given = [State()] if case.get("given_state") else []
        result = {}

        def again(inner):
            state = State()
            sink.INNER_STATES.append(state)
            return pipeline.run_async(Payload(inner), state) if run_async else pipeline.run(Payload(inner), state)

        sink.RUN_AGAIN[0] = again
        try:
            if run_async:
                out = asyncio.run(pipeline.run_async(Payload(data), *given))
            else:
                out = pipeline.run(Payload(data), *given)
            result["output"] = out.to_dict()
        except Exception as error:  # noqa: BLE001 — the error is the result
            result["error"] = f"{type(error).__name__}: {error}"

        # The State that these two lines read is that of the pipeline of the case, which this step ran.
        # It is what the case asks for, not the State of the run that this step is in.
        ran = pipeline.state  # cup: allow-state-read the State of the pipeline of the case is the result that this step reports
        result["state"] = self.report(given[0] if given else ran)
        result["pipeline_state"] = self.report(ran)
        result["inner_states"] = [self.report(state) for state in sink.INNER_STATES]
        if payload.get("hooks"):
            result["hooks"] = list(sink.HOOKS)
        result["input_after"] = data
        return payload.insert("result", result)

    def report(self, state) -> dict:
        return {"executed": list(state.executed), "skipped": list(state.skipped),
                "errors": [step for step, _error in state.errors]}
