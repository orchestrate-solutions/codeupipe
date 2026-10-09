"""The invariant linter, built as a CUP pipeline (dogfooding). Python only.

Steps:
    1. CollectFilesFilter             paths -> Python files
    2. ParsePythonFilter              files -> syntax trees (CUP-I000)
    3. AnalyzePayloadMutationFilter   CUP-I001, CUP-I002
    4. AnalyzeStateReadsFilter        CUP-I003
    5. AnalyzeOutsideWritesFilter     CUP-I004
    6. AnalyzePrimitivesPerFileFilter CUP-I005
    7. AnalyzePrimitiveNamesFilter CUP-I006, CUP-I007
    8. DropDisabledFilter       rules switched off for the project
    9. ApplySuppressionsFilter        ``cup: allow-mutation``, ``cup: allow-state-read``,
                                ``cup: allow-outside-write``, ``cup: allow-shared-file``,
                                ``cup: allow-name``
   10. FormatReportFilter             report lines + exit code
"""

import re
from typing import Iterable, Optional

from codeupipe import Payload, Pipeline
from codeupipe_lint.anonymous_steps.apply_suppressions_filter import ApplySuppressionsFilter
from codeupipe_lint.anonymous_steps.collect_files_filter import CollectFilesFilter
from codeupipe_lint.anonymous_steps.drop_disabled_filter import DropDisabledFilter
from codeupipe_lint.anonymous_steps.format_report_filter import FormatReportFilter

from .analyze_outside_writes_filter import AnalyzeOutsideWritesFilter
from .analyze_primitive_names_filter import AnalyzePrimitiveNamesFilter
from .analyze_payload_mutation_filter import AnalyzePayloadMutationFilter
from .analyze_primitives_per_file_filter import AnalyzePrimitivesPerFileFilter
from .analyze_state_reads_filter import AnalyzeStateReadsFilter
from .parse_python_filter import ParsePythonFilter

MARKER = re.compile(r"cup:\s*allow-(mutation|state-read|outside-write|shared-file|name)\b")


def build_lint_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(CollectFilesFilter())
    pipeline.add_filter(ParsePythonFilter())
    pipeline.add_filter(AnalyzePayloadMutationFilter())
    pipeline.add_filter(AnalyzeStateReadsFilter())
    pipeline.add_filter(AnalyzeOutsideWritesFilter())
    pipeline.add_filter(AnalyzePrimitivesPerFileFilter())
    pipeline.add_filter(AnalyzePrimitiveNamesFilter())
    pipeline.add_filter(DropDisabledFilter())
    pipeline.add_filter(ApplySuppressionsFilter(MARKER))
    pipeline.add_filter(FormatReportFilter("invariant violation", "invariant violations"))
    return pipeline


def lint_paths(paths: Iterable[str], exclude: Optional[Iterable[str]] = None,
               disable: Optional[Iterable[str]] = None) -> Payload:
    """Run the linter over ``paths``; the result Payload holds ``findings``,
    ``suppressed``, ``errors``, ``report``, ``error_report`` and ``exit_code``."""
    data = {"paths": list(paths), "findings": [], "errors": []}
    if exclude:
        data["exclude"] = list(exclude)
    if disable:
        data["disable"] = list(disable)
    return build_lint_pipeline().run(Payload(data))
