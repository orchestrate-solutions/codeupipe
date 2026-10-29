"""AddJudgePipeline: run the cases of ``codeupipe add`` on each target and judge them one way."""

from codeupipe import Pipeline

from .default_targets_filter import DefaultTargetsFilter
from .format_matrix_filter import FormatMatrixFilter
from .judge_add_filter import JudgeAddFilter
from .load_cases_filter import LoadCasesFilter
from .no_targets_named_predicate import NoTargetsNamedPredicate
from .run_targets_filter import RunTargetsFilter
from .summarize_filter import SummarizeFilter
from .write_results_tap import WriteResultsTap


class AddJudgePipeline(Pipeline):
    """The judge of ``add`` (conformance/ADD.md). The same steps as the judge
    of the runtimes, but for the launcher and the comparison.

    Input keys: ``cases_dir``, ``results_dir``, ``targets``, ``needs`` and
    ``names``, as JudgePipeline has them.
    Output keys: ``report``, ``matrix``, ``markdown``, ``exit_code``.
    """

    def __init__(self, launcher, node_runs_typescript, has_cargo=lambda: False, has_go=lambda: False):
        super().__init__()
        self.add_filter(LoadCasesFilter())
        self.add_valve(NoTargetsNamedPredicate(), DefaultTargetsFilter(node_runs_typescript, has_cargo, has_go))
        self.add_filter(RunTargetsFilter(launcher))
        self.add_filter(JudgeAddFilter())
        self.add_filter(SummarizeFilter())
        self.add_filter(FormatMatrixFilter())
        self.add_tap(WriteResultsTap())
