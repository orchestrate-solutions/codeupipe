"""BuildPipelineFilter: the pipeline of a case, made from its steps."""

import cup_ops as ops
from codeupipe import Payload, Pipeline

from .unsupported import Unsupported

# The reference vocabulary (conformance/README.md): for each op, how its step is made from the case.
_FILTERS = {
    "set": lambda spec: ops.SetFilter(spec["key"], spec["value"]),
    "copy": lambda spec: ops.CopyFilter(spec["from"], spec["to"]),
    "add": lambda spec: ops.AddFilter(spec["key"], spec["by"]),
    "append": lambda spec: ops.AppendFilter(spec["key"], spec["value"]),
    "remove": lambda spec: ops.RemoveFilter(spec["key"]),
    "merge": lambda spec: ops.MergeFilter(spec["value"]),
    "has": lambda spec: ops.HasFilter(spec["key"], spec["to"]),
    "mutate": lambda spec: ops.MutateFilter(spec["key"], spec["value"]),
    "fail": lambda spec: ops.FailFilter(spec["message"]),
    "run_again": lambda spec: ops.RunAgainFilter(spec["input"]),
}
_ASYNC_FILTERS = {**_FILTERS, "run_again": lambda spec: ops.AsyncRunAgainFilter(spec["input"])}
_TAPS = {
    "record": lambda spec: ops.RecordTap(spec["key"]),
    "fail": lambda spec: ops.FailTap(spec["message"]),
    "noop": lambda spec: ops.NoopTap(),
}


class BuildPipelineFilter:
    """Filter (sync).

    Input keys: ``case``, ``predicates`` (from WritePredicatesFilter),
    ``run_async``.
    Output keys: ``pipeline``, and ``label``: for each step label that the
    pipeline reports, the name that the case gives that step. Steps are
    reported by label (conformance/API.md) and the cases name them, and this
    Filter built each step, so it knows which is which. A label that is not
    in the map stays as it is, and fails the comparison.
    """

    def call(self, payload: Payload) -> Payload:
        names = {}
        pipeline = self.build(payload.get("case")["steps"], Pipeline, payload.get("predicates"),
                              names, payload.get("run_async"))
        label = {step_label: names[id(step)] for step_label, step, _type in pipeline._steps}
        return payload.insert("pipeline", pipeline).insert("label", label)

    def build(self, steps, cls, predicates, names, run_async=False):
        pipeline = cls()
        for step in steps:
            kind, name = step["kind"], step["name"]
            if kind == "filter":
                made = self.filter(step, run_async)
                pipeline.add_filter(made)
            elif kind == "tap":
                made = self.tap(step)
                pipeline.add_tap(made)
            elif kind == "valve":
                pipeline.add_valve(getattr(predicates, f"when_{name}"), self.filter(step["filter"]))
                made = pipeline._steps[-1][1]  # the Valve that the pipeline made: the step that the label names
            elif kind == "pipeline":
                made = self.build(step["steps"], ops.NestedPipeline, predicates, names)
                pipeline.add_pipeline(made)
            else:
                raise Unsupported(f"unknown step kind {kind!r}")
            names[id(made)] = name
        return pipeline

    def filter(self, spec, run_async=False):
        make = (_ASYNC_FILTERS if run_async else _FILTERS).get(spec["op"])
        if make is None:
            raise Unsupported(f"unknown filter op {spec['op']!r}")
        return make(spec)

    def tap(self, spec):
        make = _TAPS.get(spec["op"])
        if make is None:
            raise Unsupported(f"unknown tap op {spec['op']!r}")
        return make(spec)
