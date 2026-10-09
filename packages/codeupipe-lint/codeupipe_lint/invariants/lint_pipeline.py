"""The invariant linter, built as a CUP pipeline (dogfooding). Python only.

Steps:
    1. CollectFiles             paths -> Python files
    2. ParsePython              files -> syntax trees (CUP-I000)
    3. AnalyzePayloadMutation   CUP-I001, CUP-I002
    4. AnalyzeStateReads        CUP-I003
    5. AnalyzeOutsideWrites     CUP-I004
    6. AnalyzePrimitivesPerFile CUP-I005
    7. DropDisabledFilter       rules switched off for the project
    7. ApplySuppressions        ``cup: allow-mutation``, ``cup: allow-state-read``,
                                ``cup: allow-outside-write``, ``cup: allow-shared-file``
    8. FormatReport             report lines + exit code
"""

import re
from typing import Iterable, Optional

from codeupipe import Payload, Pipeline
from codeupipe_lint.anonymous_steps.apply_suppressions import ApplySuppressions
from codeupipe_lint.anonymous_steps.collect_files import CollectFiles
from codeupipe_lint.anonymous_steps.drop_disabled_filter import DropDisabledFilter
from codeupipe_lint.anonymous_steps.format_report import FormatReport

from .analyze_outside_writes import AnalyzeOutsideWrites
from .analyze_payload_mutation import AnalyzePayloadMutation
from .analyze_primitives_per_file import AnalyzePrimitivesPerFile
from .analyze_state_reads import AnalyzeStateReads
from .parse_python import ParsePython

MARKER = re.compile(r"cup:\s*allow-(mutation|state-read|outside-write|shared-file)\b")


def build_lint_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(CollectFiles())
    pipeline.add_filter(ParsePython())
    pipeline.add_filter(AnalyzePayloadMutation())
    pipeline.add_filter(AnalyzeStateReads())
    pipeline.add_filter(AnalyzeOutsideWrites())
    pipeline.add_filter(AnalyzePrimitivesPerFile())
    pipeline.add_filter(DropDisabledFilter())
    pipeline.add_filter(ApplySuppressions(MARKER))
    pipeline.add_filter(FormatReport("invariant violation", "invariant violations"))
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
