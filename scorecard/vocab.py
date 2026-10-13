"""The conformance vocabulary, reused (not reimplemented) from the Python
conformance runner: ``BuildPipelineFilter`` turns a case's steps into a live
Pipeline, ``WritePredicatesFilter`` writes Valve predicates as real
classes, and ``ExportFilter`` exports and imports the package from
disk, as a customer would.

The only thing done differently here: predicate ``def``s get index-based
names (``when_0``) instead of ``when_<step name>``, so a step name that is
not a Python identifier still builds dynamically. Whether the *export*
copes with such a name is exactly what the scorecard wants to find out.
"""

import importlib.util
import itertools
import pathlib
import sys
import tempfile
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER_DIR = ROOT / "conformance" / "runners" / "python"
# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import conformance_sink as sink  # noqa: E402
import cup_ops as ops  # noqa: E402
from case_runner.build_pipeline_filter import BuildPipelineFilter  # noqa: E402
from case_runner.export_filter import ExportFilter  # noqa: E402
from case_runner.write_predicates_filter import WritePredicatesFilter  # noqa: E402
from codeupipe import Payload, Pipeline  # noqa: E402
from codeupipe.compile.errors import UnsupportedFilterShape  # noqa: E402

__all__ = ["sink", "ops", "Payload", "Pipeline", "UnsupportedFilterShape",
           "make_predicates", "build_pipeline", "load_export", "new_workdir", "walk_steps"]

_COUNTER = itertools.count()


def new_workdir(prefix="cup_scorecard_"):
    return pathlib.Path(tempfile.mkdtemp(prefix=prefix))


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def walk_steps(steps):
    """Every step spec, depth first, nested pipelines included."""
    for step in steps:
        yield step
        if step["kind"] == "pipeline":
            yield from walk_steps(step["steps"])


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def make_predicates(steps, workdir):
    """A namespace with ``when_<step name>`` for every Valve, each a real
    ``def`` in a real file (static lowering needs its source)."""
    valves = [s for s in walk_steps(steps) if s["kind"] == "valve"]
    sources = [WritePredicatesFilter().source(str(i), s["when"]) for i, s in enumerate(valves)]
    name = f"scorecard_predicates_{next(_COUNTER)}"
    path = pathlib.Path(workdir) / f"{name}.py"
    path.write_text("\n\n".join(sources) or "\n")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # inspect.getsource resolves through sys.modules
    spec.loader.exec_module(module)
    namespace = types.SimpleNamespace()
    for i, step in enumerate(valves):
        setattr(namespace, "when_" + step["name"], getattr(module, f"when_{i}"))
    return namespace


# cup: allow-plain the differential test harness: it makes cases, runs them in each mode and compares the results
def build_pipeline(case, predicates, hooks=()):
    """The case as a live codeupipe Pipeline (BuildPipelineFilter), with ``hooks``."""
    pipeline = BuildPipelineFilter().build(case["steps"], Pipeline, predicates, {})
    for hook in hooks:
        pipeline.use_hook(hook)
    return pipeline


def load_export(pipeline, lowering, observe, workdir):
    """ExportFilter: export, write to disk, import package ``steps``."""
    return ExportFilter().load(pipeline, lowering, observe, pathlib.Path(workdir))
