"""The anonymous-step linter, built as a CUP pipeline (dogfooding).

Steps:
    1. CollectFiles       paths -> files by language
    2. AnalyzePython      ast
    3. AnalyzeGo          go/parser + go/ast (go/main.go)
    4. AnalyzeTypescript  TypeScript compiler API (ts/anonymous_steps.mjs)
    5. AnalyzeRust        lexical scan
    6. AnalyzeCpp         lexical scan
    7. AnalyzeKotlin      lexical scan
    8. AnalyzeCsharp      lexical scan
    9. ApplySuppressions  ``cup: allow-anonymous``
   10. FormatReport       report lines + exit code
"""

from typing import Iterable, Optional

from codeupipe import Payload, Pipeline

from .analyze_cpp import AnalyzeCpp
from .analyze_csharp import AnalyzeCsharp
from .analyze_go import AnalyzeGo
from .analyze_kotlin import AnalyzeKotlin
from .analyze_python import AnalyzePython
from .analyze_rust import AnalyzeRust
from .analyze_typescript import AnalyzeTypescript
from .apply_suppressions import ApplySuppressions
from .collect_files import CollectFiles
from .format_report import FormatReport


def build_lint_pipeline() -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_filter(CollectFiles())
    pipeline.add_filter(AnalyzePython())
    pipeline.add_filter(AnalyzeGo())
    pipeline.add_filter(AnalyzeTypescript())
    pipeline.add_filter(AnalyzeRust())
    pipeline.add_filter(AnalyzeCpp())
    pipeline.add_filter(AnalyzeKotlin())
    pipeline.add_filter(AnalyzeCsharp())
    pipeline.add_filter(ApplySuppressions())
    pipeline.add_filter(FormatReport())
    return pipeline


def lint_paths(paths: Iterable[str], languages: Optional[Iterable[str]] = None,
               exclude: Optional[Iterable[str]] = None) -> Payload:
    """Run the linter over ``paths``; the result Payload holds ``findings``,
    ``suppressed``, ``errors``, ``report``, ``error_report`` and ``exit_code``."""
    data = {"paths": list(paths), "findings": [], "errors": []}
    if languages:
        data["languages"] = list(languages)
    if exclude:
        data["exclude"] = list(exclude)
    return build_lint_pipeline().run(Payload(data))
