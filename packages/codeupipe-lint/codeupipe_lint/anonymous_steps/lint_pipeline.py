"""The anonymous-step linter, built as a CUP pipeline (dogfooding). Python only.

Steps:
    1. CollectFilesFilter       paths -> Python files
    2. AnalyzePythonFilter      ast
    3. DropDisabledFilter rules switched off for the project
    4. ApplySuppressionsFilter  ``cup: allow-anonymous``
    5. FormatReportFilter       report lines + exit code
"""

from typing import Iterable, Optional

from codeupipe import Payload, Pipeline

from .analyze_python_filter import AnalyzePythonFilter
from .apply_suppressions_filter import ApplySuppressionsFilter
from .collect_files_filter import CollectFilesFilter
from .drop_disabled_filter import DropDisabledFilter
from .format_report_filter import FormatReportFilter


def build_lint_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(CollectFilesFilter())
    pipeline.add_filter(AnalyzePythonFilter())
    pipeline.add_filter(DropDisabledFilter())
    pipeline.add_filter(ApplySuppressionsFilter())
    pipeline.add_filter(FormatReportFilter())
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
