"""Step identity: a pointer to the filter, derived from the code (conformance/API.md).

No step names. A step is identified by its filter's fully qualified symbol,
``#n`` when the same one is used again in a pipeline; the add site
(file:line) is recorded as extra detail. Anonymous steps are refused.
"""

import pytest

from codeupipe import Hook, Payload, Pipeline, Valve
from codeupipe.core import AnonymousStep

MODULE = __name__


class Add:
    def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


class Boom:
    def call(self, payload):
        raise RuntimeError("boom")


class Audit:
    def observe(self, payload):
        pass


class UserOnboarding(Pipeline):
    """A named pipeline type: nestable, identified like a filter."""

    def __init__(self):
        super().__init__()
        self.add_filter(Add())


class IsOn:
    """A predicate object: test(payload) -> bool, identified by its class."""

    def test(self, payload):
        return bool(payload.get("on"))


class AtLeast:
    """A configurable predicate: its setting lives on the instance."""

    def __init__(self, n):
        self.n = n

    def test(self, payload):
        return payload.get("n", 0) >= self.n


def is_on(payload):
    return bool(payload.get("on"))


class Record(Hook):
    def __init__(self):
        self.events = []

    def before(self, step, payload):
        self.events.append(("before", step))

    def after(self, step, payload):
        self.events.append(("after", step))

    def on_error(self, step, error, payload):
        self.events.append(("error", step))


def _pipeline(*steps):
    p = Pipeline()
    for step in steps:
        p.add_filter(step)
    return p


class TestIdentityIsTheFiltersSymbol:
    def test_state_reports_the_qualified_symbol(self):
        p = _pipeline(Add())
        p.run(Payload({}))
        assert p.state.executed == [f"{MODULE}.Add"]

    def test_reuse_is_numbered_from_the_second_occurrence(self):
        p = _pipeline(Add(), Add(), Add())
        p.run(Payload({}))
        assert p.state.executed == [f"{MODULE}.Add", f"{MODULE}.Add#2", f"{MODULE}.Add#3"]

    def test_taps_are_identified_the_same_way(self):
        p = _pipeline(Add())
        p.add_tap(Audit())
        p.run(Payload({}))
        assert p.state.executed == [f"{MODULE}.Add", f"{MODULE}.Audit"]

    def test_hooks_receive_the_identity(self):
        p = _pipeline(Add(), Boom())
        hook = Record()
        p.use_hook(hook)
        with pytest.raises(RuntimeError):
            p.run(Payload({}))
        assert hook.events == [("before", None), ("before", f"{MODULE}.Add"), ("after", f"{MODULE}.Add"),
                               ("before", f"{MODULE}.Boom"), ("error", f"{MODULE}.Boom"), ("error", None)]

    def test_a_valve_is_identified_by_its_inner_filter(self):
        p = Pipeline()
        p.add_filter(Valve(Add(), IsOn()))
        p.run(Payload({}))
        assert p.state.skipped == [f"{MODULE}.Add"]

    def test_a_valve_and_a_plain_use_of_the_same_filter_are_numbered(self):
        p = _pipeline(Add())
        p.add_filter(Valve(Add(), IsOn()))
        p.run(Payload({"on": True}))
        assert p.state.executed == [f"{MODULE}.Add", f"{MODULE}.Add#2"]

    def test_a_named_pipeline_type_nests_as_one_step(self):
        outer = _pipeline(Add())
        outer.add_pipeline(UserOnboarding())
        assert outer.run(Payload({})).get("n") == 2
        assert outer.state.executed == [f"{MODULE}.Add", f"{MODULE}.UserOnboarding"]

    def test_identities_lists_steps_in_order(self):
        p = _pipeline(Add(), Add())
        assert p.identities == [f"{MODULE}.Add", f"{MODULE}.Add#2"]


class TestPredicateObjects:
    def test_the_predicate_is_identified_by_its_class(self):
        assert Valve(Add(), IsOn()).predicate_symbol == f"{MODULE}.IsOn"

    def test_a_configurable_predicate(self):
        p = Pipeline()
        p.add_filter(Valve(Add(), AtLeast(5)))
        assert p.run(Payload({"n": 5})).get("n") == 6
        assert p.run(Payload({"n": 1})).get("n") == 1


class TestAddSite:
    def test_the_add_call_location_is_recorded(self):
        p = Pipeline()
        p.add_filter(Add())  # this line
        site = p.step_sites[f"{MODULE}.Add"]
        assert site.endswith("test_step_identity.py:%d" % (TestAddSite.line_of_add_call(),))

    @staticmethod
    def line_of_add_call():
        import inspect
        source, start = inspect.getsourcelines(TestAddSite.test_the_add_call_location_is_recorded)
        return start + next(i for i, line in enumerate(source) if "# this line" in line)


def _make_closure_filter():
    class Local:
        def call(self, payload):
            return payload
    return Local()


def _make_closure_predicate():
    def inner(payload):
        return True
    return inner


class TestAnonymousStepsAreRefused:
    def test_class_defined_in_a_function(self):
        with pytest.raises(AnonymousStep, match="Local"):
            Pipeline().add_filter(_make_closure_filter())  # cup: allow-anonymous (exercises the refusal)

    def test_a_function_is_not_a_predicate(self):
        with pytest.raises(AnonymousStep, match="predicate object"):
            Valve(Add(), is_on)  # cup: allow-anonymous (exercises the refusal)

    def test_lambda_predicate(self):
        with pytest.raises(AnonymousStep, match="lambda"):
            Valve(Add(), lambda payload: True)  # cup: allow-anonymous (exercises the refusal)

    def test_closure_predicate(self):
        with pytest.raises(AnonymousStep, match="inner"):
            Valve(Add(), _make_closure_predicate())  # cup: allow-anonymous (exercises the refusal)

    def test_filter_defined_in_the_entry_script(self):
        Main = type("Main", (), {"call": lambda self, payload: payload, "__module__": "__main__"})
        with pytest.raises(AnonymousStep, match="__main__"):
            Pipeline().add_filter(Main())

    def test_plain_pipeline_cannot_be_nested(self):
        with pytest.raises(AnonymousStep, match="named Pipeline type"):
            Pipeline().add_pipeline(_pipeline(Add()))  # cup: allow-anonymous (exercises the refusal)

    def test_the_message_names_the_fix(self):
        with pytest.raises(AnonymousStep) as info:
            Pipeline().add_filter(_make_closure_filter())  # cup: allow-anonymous (exercises the refusal)
        assert "module level" in str(info.value)

    def test_anonymous_step_is_a_type_error(self):
        assert issubclass(AnonymousStep, TypeError)


class TestNamesAreGone:
    def test_add_filter_takes_no_name(self):
        with pytest.raises(TypeError):
            Pipeline().add_filter(Add(), "add")  # type: ignore[call-arg]

    def test_valve_takes_no_name(self):
        with pytest.raises(TypeError):
            Valve("gate", Add(), IsOn())  # type: ignore[call-arg]


