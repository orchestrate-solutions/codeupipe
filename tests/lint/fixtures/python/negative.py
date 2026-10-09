"""Named steps the Python analyzer must NOT flag."""

from codeupipe import Pipeline, Valve


class Add:
    def call(self, payload):
        return payload


class Audit:
    def observe(self, payload):
        pass


class UserOnboarding(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(Add())


class IsOn:
    """A predicate object (conformance/API.md, "Valve")."""

    def test(self, payload):
        return True


def make_add():
    return Add()


def build(steps, predicate):
    p = Pipeline()
    p.add_filter(Add())
    p.add_filter(Add)
    p.add_tap(Audit())
    p.add_filter(Valve(Add(), IsOn()))
    p.add_pipeline(UserOnboarding())
    p.add_filter(make_add())
    for step in steps:
        p.add_filter(step)  # a parameter: unknown, not flagged
    p.add_filter(Valve(Add(), predicate))

    # Not steps: lambdas elsewhere are fine.
    key = sorted([3, 1], key=lambda x: -x)
    p.on("step_start", lambda event: None)
    p.use_hook(object())

    # A name rebound from a lambda to a named filter is not provably anonymous.
    step = lambda payload: payload  # noqa: E731
    step = Add()
    p.add_filter(step)

    # Shadowing: the parameter hides the module-level lambda of the same name.
    return p, key


GLOBAL_LAMBDA = lambda payload: payload  # noqa: E731


def shadowed(GLOBAL_LAMBDA):
    p = Pipeline()
    p.add_filter(GLOBAL_LAMBDA)
    return p


def plain_pipeline_at_top_level():
    p = Pipeline()  # a plain Pipeline may run at the top level
    p.add_filter(Add())
    return p.run
