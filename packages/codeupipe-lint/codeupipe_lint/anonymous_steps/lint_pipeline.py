"""The anonymous-step linter, built as a CUP pipeline (dogfooding). Python only.

Steps:
    1. CollectFiles       paths -> Python files
    2. AnalyzePython      ast
    3. DropDisabledFilter rules switched off for the project
    4. ApplySuppressions  ``cup: allow-anonymous``
    5. FormatReport       report lines + exit code
"""

from typing import Iterable, Optional

from codeupipe import Payload, Pipeline

from .analyze_python import AnalyzePython
from .apply_suppressions import ApplySuppressions
from .collect_files import CollectFiles
from .drop_disabled_filter import DropDisabledFilter
from .format_report import FormatReport


def build_lint_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(CollectFiles())
    pipeline.add_filter(AnalyzePython())
    pipeline.add_filter(DropDisabledFilter())
    pipeline.add_filter(ApplySuppressions())
    pipeline.add_filter(FormatReport())
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
