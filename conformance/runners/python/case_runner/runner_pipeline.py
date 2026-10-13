"""RunnerPipeline: the whole runner for one call: each case, or each scenario, on one target."""

from codeupipe import Pipeline


class RunnerPipeline(Pipeline):
    """Input keys: ``cases``, ``target``. Output keys: ``results``.

    ``each`` is the Filter that goes through the cases: RunEachCaseFilter to
    play them, or BenchEachScenarioFilter to time them.
    """

    def __init__(self, each):
        super().__init__()
        self.add_filter(each)
