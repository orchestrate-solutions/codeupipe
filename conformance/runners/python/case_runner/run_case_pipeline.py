"""RunCasePipeline: play one conformance case on one target and report what happened."""

from codeupipe import Pipeline

from .attach_record_hook_filter import AttachRecordHookFilter
from .build_pipeline_filter import BuildPipelineFilter
from .export_filter import ExportFilter
from .finish_result_filter import FinishResultFilter
from .is_compiled_predicate import IsCompiledPredicate
from .name_steps_filter import NameStepsFilter
from .parse_target_filter import ParseTargetFilter
from .run_compiled_filter import RunCompiledFilter
from .run_dynamic_filter import RunDynamicFilter
from .write_predicates_filter import WritePredicatesFilter


class RunCasePipeline(Pipeline):
    """Input keys: ``case``, ``target``, ``workdir``, ``module_name``.
    Output keys: ``result`` (conformance/README.md, "Runner protocol").

    The runner never judges. A step that raises Unsupported, or any other
    error before the case runs, means that the target cannot express the
    case: RunEachCaseFilter reports that.
    """

    def __init__(self):
        super().__init__()
        self.add_filter(ParseTargetFilter())
        self.add_filter(WritePredicatesFilter())
        self.add_filter(BuildPipelineFilter())
        self.add_filter(AttachRecordHookFilter())
        self.add_valve(IsCompiledPredicate(), ExportFilter())
        self.add_valve(IsCompiledPredicate(False), RunDynamicFilter())
        self.add_valve(IsCompiledPredicate(), RunCompiledFilter())
        self.add_filter(NameStepsFilter())
        self.add_filter(FinishResultFilter())
