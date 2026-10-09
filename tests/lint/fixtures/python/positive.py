"""Anonymous steps the Python analyzer must flag. Each flagged line carries
an ``expect:`` comment naming the rule; the test compares them exactly."""

from codeupipe import Pipeline, Valve
import codeupipe


class Add:
    def call(self, payload):
        return payload


def is_on(payload):
    return True


GLOBAL_LAMBDA = lambda payload: payload  # noqa: E731


def make_closure(k):
    def inner(payload):
        return payload
    return inner


def make_local_class():
    class Local:
        def call(self, payload):
            return payload
    return Local()


def make_lambda():
    return lambda payload: payload


def build():
    p = Pipeline()
    p.add_filter(lambda payload: payload)  # expect: CUP-A001
    p.add_tap(lambda payload: None)  # expect: CUP-A001
    p.add_async_filter(lambda payload: payload)  # expect: CUP-A001
    p.add_async_tap(lambda payload: None)  # expect: CUP-A001
    p.insert_filter_after("x", lambda payload: payload)  # expect: CUP-A001
    p.add_filter(Valve(Add(), lambda payload: True))  # expect: CUP-A001
    p.add_filter(codeupipe.Valve(Add(), lambda payload: True))  # expect: CUP-A001

    def nested(payload):
        return payload

    class LocalFilter:
        def call(self, payload):
            return payload

    p.add_filter(nested)  # expect: CUP-A002
    p.add_filter(LocalFilter())  # expect: CUP-A003
    p.add_filter(LocalFilter)  # expect: CUP-A003
    p.add_filter(Valve(LocalFilter(), is_on))  # expect: CUP-A003 CUP-A008
    p.add_filter(Valve(Add(), nested))  # expect: CUP-A002
    p.add_parallel([Add(), lambda payload: payload, LocalFilter()])  # expect: CUP-A001 CUP-A003

    bound = lambda payload: payload  # noqa: E731
    p.add_filter(bound)  # expect: CUP-A001
    instance = LocalFilter()
    p.add_tap(instance)  # expect: CUP-A003
    p.add_filter(GLOBAL_LAMBDA)  # expect: CUP-A001

    p.add_filter(make_closure("x"))  # expect: CUP-A002
    p.add_filter(make_local_class())  # expect: CUP-A003
    p.add_filter(Valve(Add(), make_lambda()))  # expect: CUP-A001

    sub = Pipeline()
    sub.add_filter(Add())
    p.add_pipeline(sub)  # expect: CUP-A005
    p.add_pipeline(Pipeline())  # expect: CUP-A005
    p.add_pipeline(codeupipe.Pipeline())  # expect: CUP-A005

    class LocalPipeline(Pipeline):
        pass

    p.add_pipeline(LocalPipeline())  # expect: CUP-A003
    p.add_filter(
        lambda payload: payload,  # expect: CUP-A001
    )
    return p


class Builder:
    def build(self):
        p = Pipeline()

        class Inner:
            def call(self, payload):
                return payload

        p.add_filter(Inner())  # expect: CUP-A003
        return p

    def closure_in_method(self):
        def pred(payload):
            return True

        return Valve(Add(), pred)  # expect: CUP-A002


def is_on(payload):
    return True


def function_predicates():
    # Valve predicates are objects: a named function is not one.
    return Valve(Add(), is_on)  # expect: CUP-A008
