"""A step is reported by a label: the name of its class.

State and Hooks use the label. Nothing is refused for its name: a class in a
script, a class in a function and a plain nested Pipeline all work. The
linter is the guard for names.
"""

import pytest

import codeupipe
from codeupipe import Hook, Payload, Pipeline


class AddFilter:
    def call(self, payload):
        return payload.insert("n", payload.get("n", 0) + 1)


class FailFilter:
    def call(self, payload):
        raise RuntimeError("boom")


class SeeTap:
    def observe(self, payload):
        pass


class IsOnPredicate:
    def test(self, payload):
        return payload.get("on") is True


class InnerPipeline(Pipeline):
    def __init__(self):
        super().__init__()
        self.add_filter(AddFilter())


class RecordHook(Hook):
    def __init__(self):
        self.events = []

    def before(self, step, payload):
        self.events.append(("before", step))

    def after(self, step, payload):
        self.events.append(("after", step))

    def on_error(self, step, error, payload):
        self.events.append(("error", step))


def test_the_label_is_the_class_name():
    pipeline = Pipeline()
    pipeline.add_filter(AddFilter())
    pipeline.add_tap(SeeTap())
    assert pipeline.labels == ["AddFilter", "SeeTap"]


def test_state_reports_labels():
    pipeline = Pipeline()
    pipeline.add_filter(AddFilter())
    pipeline.add_tap(SeeTap())
    pipeline.run(Payload({}))
    assert pipeline.state.executed == ["AddFilter", "SeeTap"]


def test_the_second_use_of_a_class_gets_a_number():
    pipeline = Pipeline()
    for _ in range(3):
        pipeline.add_filter(AddFilter())
    assert pipeline.labels == ["AddFilter", "AddFilter#2", "AddFilter#3"]
    assert pipeline.run(Payload({})).get("n") == 3
    assert pipeline.state.executed == ["AddFilter", "AddFilter#2", "AddFilter#3"]


def test_a_valve_has_the_label_of_its_filter():
    pipeline = Pipeline()
    pipeline.add_valve(IsOnPredicate(), AddFilter())
    assert pipeline.labels == ["AddFilter"]
    pipeline.run(Payload({"on": False}))
    assert pipeline.state.skipped == ["AddFilter"]


def test_a_nested_pipeline_has_the_label_of_its_class():
    outer = Pipeline()
    outer.add_pipeline(InnerPipeline())
    assert outer.labels == ["InnerPipeline"]
    outer.run(Payload({}))
    assert outer.state.executed == ["InnerPipeline"]


def test_a_plain_nested_pipeline_is_accepted():
    inner = Pipeline()
    inner.add_filter(AddFilter())
    outer = Pipeline()
    outer.add_pipeline(inner)  # cup: allow-anonymous (a plain nested Pipeline works at run time)
    assert outer.labels == ["Pipeline"]
    assert outer.run(Payload({})).get("n") == 1


def test_hooks_receive_labels():
    hook = RecordHook()
    pipeline = Pipeline()
    pipeline.add_filter(AddFilter())
    pipeline.use_hook(hook)
    pipeline.run(Payload({}))
    assert hook.events == [("before", None), ("before", "AddFilter"), ("after", "AddFilter"), ("after", None)]


def test_an_error_names_the_label():
    hook = RecordHook()
    pipeline = Pipeline()
    pipeline.add_filter(FailFilter())
    pipeline.use_hook(hook)
    with pytest.raises(RuntimeError):
        pipeline.run(Payload({}))
    assert ("error", "FailFilter") in hook.events


def test_a_class_defined_in_a_function_works():
    class LocalFilter:
        def call(self, payload):
            return payload.insert("local", True)

    pipeline = Pipeline()
    pipeline.add_filter(LocalFilter())  # cup: allow-anonymous (a local class works at run time)
    assert pipeline.labels == ["LocalFilter"]
    assert pipeline.run(Payload({})).get("local") is True


def test_a_class_from_the_entry_script_works():
    script_class = type("ScriptFilter", (), {"__module__": "__main__",
                                             "call": lambda self, payload: payload.insert("s", 1)})
    pipeline = Pipeline()
    pipeline.add_filter(script_class())
    assert pipeline.labels == ["ScriptFilter"]
    assert pipeline.run(Payload({})).get("s") == 1


@pytest.mark.parametrize("add, bad, says", [
    ("add_filter", lambda payload: payload, "call(payload)"),
    ("add_filter", object(), "call(payload)"),
    ("add_tap", object(), "observe(payload)"),
    ("add_pipeline", object(), "Pipeline"),
])
def test_a_step_with_the_wrong_shape_is_refused_when_it_is_added(add, bad, says):
    with pytest.raises(TypeError) as error:
        getattr(Pipeline(), add)(bad)  # cup: allow-anonymous (exercises the refusal)
    assert says in str(error.value)


def test_a_predicate_with_no_test_method_is_refused():
    def is_on(payload):
        return True
    with pytest.raises(TypeError) as error:
        Pipeline().add_valve(is_on, AddFilter())  # cup: allow-anonymous (exercises the refusal)
    assert "test(payload)" in str(error.value)


def test_a_name_argument_is_not_accepted():
    with pytest.raises(TypeError):
        Pipeline().add_filter(AddFilter(), "a_name")


def test_the_identity_names_are_gone():
    assert "AnonymousStep" not in codeupipe.__all__
    assert not hasattr(Pipeline(), "identities")
    assert not hasattr(Pipeline(), "step_sites")
