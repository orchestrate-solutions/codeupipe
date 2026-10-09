"""Every flagged line carries an ``expect:`` comment with its rule id."""

from codeupipe.core import Pipeline, State

PIPELINE = Pipeline()


class ReadsThroughAPipelineItHolds:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def call(self, payload):
        if "validate" in self.pipeline.state.executed:  # expect: CUP-I003
            return payload.insert("validated", True)
        return payload


class ReadsAModuleLevelPipeline:
    def call(self, payload):
        return payload.insert("errors", len(PIPELINE.state.errors))  # expect: CUP-I003


class ReadsTimings:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def call(self, payload):
        return payload.insert("flag", self.pipeline.state.timings.get("flag"))  # expect: CUP-I003


class WritesState:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def call(self, payload):
        self.pipeline.state.mark_executed("seen")  # expect: CUP-I003
        return payload


class HoldsTheStateItself:
    def __init__(self, state: State):
        self.run_state = state

    def call(self, payload):
        return payload.insert("skipped", list(self.run_state.skipped))  # expect: CUP-I003


class HoldsAStateTakenFromAPipeline:
    def __init__(self, pipeline):
        self.progress = pipeline.state

    def call(self, payload):
        return payload.insert("n", len(self.progress.executed))  # expect: CUP-I003


class BuildsItsOwnState:
    def __init__(self):
        self.ledger = State()

    def call(self, payload):
        self.ledger.mark_executed("x")  # expect: CUP-I003
        return payload


class BindsStateToALocal:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def call(self, payload):
        state = self.pipeline.state  # expect: CUP-I003
        return payload.insert("n", len(state.timings))


class PredicateReadsState:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def test(self, payload):
        return not self.pipeline.state.errors  # expect: CUP-I003


class AsyncFilterReadsState:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    async def call(self, payload):
        return payload.insert("t", self.pipeline.state.timings)  # expect: CUP-I003
