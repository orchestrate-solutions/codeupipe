"""WritePredicatesFilter: the Predicates of a case, as real classes in a module on disk."""

import importlib
import json
import sys

from codeupipe import Payload

from .unsupported import Unsupported


class WritePredicatesFilter:
    """Filter (sync).

    Input keys: ``case``, ``workdir`` (a directory for this case),
    ``module_name``.
    Output keys: ``predicates``: a module that has, for each Valve of the
    case, an instance ``when_<name>`` of a Predicate class.

    The Predicates are written as source code and imported, because the
    compiler reads the source of a Predicate and refuses anything else.
    """

    def call(self, payload: Payload) -> Payload:
        workdir, module_name = payload.get("workdir"), payload.get("module_name")
        sources = self.sources(payload.get("case")["steps"])
        (workdir / f"{module_name}.py").write_text("\n\n".join(sources) or "\n")
        sys.path.insert(0, str(workdir))
        try:
            return payload.insert("predicates", importlib.import_module(module_name))
        finally:
            sys.path.remove(str(workdir))

    def sources(self, steps) -> list:
        """The source of the Predicate of each Valve, with those of the nested pipelines."""
        found = []
        for step in steps:
            if step["kind"] == "valve":
                found.append(self.source(step["name"], step["when"]))
            elif step["kind"] == "pipeline":
                found.extend(self.sources(step["steps"]))
        return found

    def source(self, name, when) -> str:
        key = json.dumps(when["key"])
        if when["op"] == "equals":
            body = f"payload.get({key}) == {when['value']!r}"
        elif when["op"] == "truthy":
            body = f"bool(payload.get({key}))"
        else:
            raise Unsupported(f"unknown valve op {when['op']!r}")
        # a predicate object (conformance/API.md, "Valve"): a class with test(),
        # plus a module-level instance under the name the builders look up
        return (f"class When_{name}:\n    def test(self, payload):\n        return {body}\n\n\n"
                f"when_{name} = When_{name}()\n")
