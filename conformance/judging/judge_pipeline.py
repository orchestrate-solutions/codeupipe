"""JudgePipeline: run the conformance cases on each target and judge them one way."""

from codeupipe import Pipeline

from .default_targets_filter import DefaultTargetsFilter
from .format_matrix_filter import FormatMatrixFilter
from .judge_results_filter import JudgeResultsFilter
from .load_cases_filter import LoadCasesFilter
from .no_targets_named_predicate import NoTargetsNamedPredicate
from .run_targets_filter import RunTargetsFilter
from .summarize_filter import SummarizeFilter
from .write_results_tap import WriteResultsTap


class JudgePipeline(Pipeline):
    """The judge.

    Input keys: ``cases_dir``, ``results_dir``, ``targets`` ({name: how to
    start its runner}), ``needs`` ({name: paths that the target needs}), and
    ``names`` (the targets that the caller named; empty for each target that
    this machine can run).
    Output keys: ``report``, ``matrix``, ``markdown``, ``exit_code``.

    ``launcher`` starts the runner of a target. ``node_runs_typescript`` says
    if the machine can run the TypeScript targets.
    """

    def __init__(self, launcher, node_runs_typescript):
        super().__init__()
        self.add_filter(LoadCasesFilter())
        self.add_valve(NoTargetsNamedPredicate(), DefaultTargetsFilter(node_runs_typescript))
        self.add_filter(RunTargetsFilter(launcher))
        self.add_filter(JudgeResultsFilter())
        self.add_filter(SummarizeFilter())
        self.add_filter(FormatMatrixFilter())
        self.add_tap(WriteResultsTap())
