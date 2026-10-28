"""BenchScenarioPipeline: time one scenario on one target."""

from codeupipe import Pipeline

from .attach_noop_hook_filter import AttachNoopHookFilter
from .build_pipeline_filter import BuildPipelineFilter
from .export_filter import ExportFilter
from .is_compiled_predicate import IsCompiledPredicate
from .make_run_function_filter import MakeRunFunctionFilter
from .measure_filter import MeasureFilter
from .parse_target_filter import ParseTargetFilter
from .write_predicates_filter import WritePredicatesFilter

TARGETS = ("run", "static-steps", "static-inline", "static-observe")


class BenchScenarioPipeline(Pipeline):
    """Input keys: ``case`` (a scenario), ``target``, ``workdir``, ``module_name``.
    Output keys: ``us_per_run``, ``relative``, ``output``.
    """

    def __init__(self):
        super().__init__()
        self.add_filter(ParseTargetFilter(TARGETS, "bench target"))
        self.add_filter(WritePredicatesFilter())
        self.add_filter(BuildPipelineFilter())
        self.add_filter(AttachNoopHookFilter())
        self.add_valve(IsCompiledPredicate(), ExportFilter())
        self.add_filter(MakeRunFunctionFilter())
        self.add_filter(MeasureFilter())
