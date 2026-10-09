"""AnalyzeTypescript: anonymous steps in TypeScript files, via the TypeScript
compiler API (``ts/anonymous_steps.mjs``, run with bun or node).

The compiler is found at CUP_LINT_TYPESCRIPT (the ``typescript`` package
directory), else ``runtimes/ts/node_modules/typescript`` (``npm ci`` in
runtimes/ts). With codeupipe's build step, the TypeScript runtime already
refuses every anonymous step; this gives the same feedback at authoring time.
"""

import json
import os
import subprocess

from codeupipe import Payload

from .rules import make_finding
from .toolchain import HERE, REPO, find_tool

SCRIPT = os.path.join(HERE, "ts", "anonymous_steps.mjs")
DEFAULT_TYPESCRIPT = os.path.join(REPO, "runtimes", "ts", "node_modules", "typescript")
BUN_CANDIDATES = ["~/.bun/bin/bun"]
NODE_CANDIDATES = ["/usr/local/bin/node", "/opt/homebrew/bin/node"]


class AnalyzeTypescript:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``, ``errors``.
    Output keys: ``findings`` (TypeScript findings appended), ``errors``
    (appended when no JS runtime or TypeScript compiler is found).
    """

    def __init__(self, runtime: str = None, typescript: str = None):
        self._runtime = runtime
        self._typescript = typescript

    def call(self, payload: Payload) -> Payload:
        paths = payload.get("files", {}).get("ts", [])
        if not paths:
            return payload
        findings = list(payload.get("findings", []))
        errors = list(payload.get("errors", []))
        try:
            records = self._run(paths)
        except RuntimeError as error:
            errors.append("ts: %s; %d TypeScript file(s) not checked" % (error, len(paths)))
            return payload.insert("errors", errors)
        for r in records:
            findings.append(make_finding("ts", r["path"], r["line"], r["col"], r["rule"], r["role"], r["what"],
                                         r.get("call_line")))
        return payload.insert("findings", findings).insert("errors", errors)

    def _run(self, paths):
        runtime = self._runtime or find_tool("bun", BUN_CANDIDATES) or find_tool("node", NODE_CANDIDATES)
        if not runtime or not os.path.exists(runtime):
            raise RuntimeError("no JavaScript runtime found (install bun or node)")
        typescript = self._typescript or os.environ.get("CUP_LINT_TYPESCRIPT") or DEFAULT_TYPESCRIPT
        if not os.path.isfile(os.path.join(typescript, "package.json")):
            raise RuntimeError("TypeScript compiler not found at %s (run `npm ci` in runtimes/ts, or set "
                               "CUP_LINT_TYPESCRIPT to a typescript package directory)" % typescript)
        absolute = {os.path.abspath(p): p for p in paths}
        proc = subprocess.run([runtime, SCRIPT, os.path.join(typescript, "lib", "typescript.js")],
                              input="\n".join(absolute), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("the TypeScript analyzer failed: " + proc.stderr.strip())
        records = []
        for line in proc.stdout.splitlines():
            record = json.loads(line)
            record["path"] = absolute.get(record["path"], record["path"])
            records.append(record)
        return records
