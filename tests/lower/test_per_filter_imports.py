"""Per-filter imports flow only into the files that need them."""

import asyncio
import math
import json

from codeupipe import Payload, Pipeline
from codeupipe.lower import build_export_pipeline_v2


class _UsesMath:
    def call(self, payload):
        return payload.insert("floor", math.floor(payload.get("x", 0.0)))


class _UsesJson:
    def call(self, payload):
        return payload.insert("dumped", json.dumps(payload.get("obj", {})))


class _UsesNothing:
    def call(self, payload):
        return payload.insert("touched", True)


def _export(pipeline: Pipeline):
    exp = build_export_pipeline_v2(write=False)
    result = asyncio.run(exp.run_async(Payload({"pipeline": pipeline, "pattern": "flat"})))
    return {f["path"]: f["content"] for f in result.get("files") or []}


class TestPerFilterImports:
    def test_only_math_step_imports_math(self):
        p = Pipeline()
        p.add_filter(_UsesMath())
        p.add_filter(_UsesNothing())

        files = _export(p)
        math_file    = next(c for path, c in files.items() if path.endswith("uses_math.py"))
        nothing_file = next(c for path, c in files.items() if path.endswith("uses_nothing.py"))

        assert "import math" in math_file
        assert "import math" not in nothing_file

    def test_only_json_step_imports_json(self):
        p = Pipeline()
        p.add_filter(_UsesJson())
        p.add_filter(_UsesNothing())

        files = _export(p)
        json_file    = next(c for path, c in files.items() if path.endswith("uses_json.py"))
        nothing_file = next(c for path, c in files.items() if path.endswith("uses_nothing.py"))

        assert "import json" in json_file
        assert "import json" not in nothing_file

    def test_imports_do_not_leak_across_step_files(self):
        p = Pipeline()
        p.add_filter(_UsesMath())
        p.add_filter(_UsesJson())

        files = _export(p)
        math_file = next(c for path, c in files.items() if path.endswith("uses_math.py"))
        json_file = next(c for path, c in files.items() if path.endswith("uses_json.py"))

        assert "import math" in math_file
        assert "import json" not in math_file
        assert "import json" in json_file
        assert "import math" not in json_file
