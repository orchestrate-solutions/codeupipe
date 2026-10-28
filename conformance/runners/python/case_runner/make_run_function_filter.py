"""MakeRunFunctionFilter: the one function that a measurement calls again and again."""

from codeupipe import Payload


class MakeRunFunctionFilter:
    """Filter (sync).

    Input keys: ``case`` (a scenario), ``compiled``, ``observe``, ``hooks``,
    and ``pipeline`` or ``package``.
    Output keys: ``fn``: a function with no arguments that does one run of
    the scenario on a new copy of its input. ``output``: what one run gives.
    """

    def call(self, payload: Payload) -> Payload:
        fn = self.make(payload)
        return payload.insert("fn", fn).insert("output", self.output(fn(), payload.get("compiled")))

    def make(self, payload: Payload):
        data = payload.get("case")["input"]
        if not payload.get("compiled"):
            pipeline = payload.get("pipeline")
            return lambda: pipeline.run(Payload(dict(data)))
        run = payload.get("package").run
        if not payload.get("observe"):
            return lambda: run(dict(data))
        hooks = payload.get("hooks")
        state = {}
        return lambda: run(dict(data), state=state, hooks=hooks)

    def output(self, out, compiled):
        """The dynamic run gives a Payload, and compiled code gives a dict."""
        return out if compiled else out.to_dict()
