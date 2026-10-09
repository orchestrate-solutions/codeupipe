"""AnalyzeGo: anonymous steps in Go files, via go/parser + go/ast.

The analysis is the Go program in ``go/main.go`` (stdlib Go only), built
once per source revision into the cache (toolchain.cache_dir) and fed the
file list on stdin. For Go, a type declared inside a function looks like a
package-level type at runtime, so this
analyzer is the only check for CUP-A003.
"""

import json
import os
import subprocess

from codeupipe import Payload

from .rules import make_finding
from .toolchain import HERE, cache_dir, digest, find_tool

GO_DIR = os.path.join(HERE, "go")
GO_CANDIDATES = ["/usr/local/go/bin/go", "/opt/homebrew/bin/go", "~/go/bin/go", "~/sdk/go/bin/go"]


class AnalyzeGo:
    """Filter (sync).

    Input keys: ``files`` ({lang: [path]}), ``findings``, ``errors``.
    Output keys: ``findings`` (Go findings appended), ``errors`` (appended
    when the Go toolchain is missing or the helper fails: Go files unchecked).
    """

    def __init__(self, go: str = None):
        self._go = go

    def call(self, payload: Payload) -> Payload:
        paths = payload.get("files", {}).get("go", [])
        if not paths:
            return payload
        findings = list(payload.get("findings", []))
        errors = list(payload.get("errors", []))
        try:
            records = self._run(paths)
        except RuntimeError as error:
            errors.append("go: %s; %d Go file(s) not checked" % (error, len(paths)))
            return payload.insert("errors", errors)
        for r in records:
            findings.append(make_finding("go", r["path"], r["line"], r["col"], r["rule"], r["role"], r["what"],
                                         r.get("call_line")))
        return payload.insert("findings", findings).insert("errors", errors)

    def _binary(self) -> str:
        go = self._go or find_tool("go", GO_CANDIDATES)
        if not go or not os.path.exists(go):
            raise RuntimeError("Go toolchain not found (install Go, or put `go` on PATH)")
        sources = [os.path.join(GO_DIR, "main.go"), os.path.join(GO_DIR, "go.mod")]
        binary = os.path.join(cache_dir(), "go-anonymous-steps-" + digest(sources))
        if not os.path.exists(binary):
            env = dict(os.environ, GOWORK="off", GOFLAGS="-mod=mod")
            proc = subprocess.run([go, "build", "-o", binary + ".tmp", "."], cwd=GO_DIR, env=env,
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError("building the Go analyzer failed: " + proc.stderr.strip())
            os.replace(binary + ".tmp", binary)
        return binary

    def _run(self, paths):
        proc = subprocess.run([self._binary()], input="\n".join(os.path.abspath(p) for p in paths),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("the Go analyzer failed: " + proc.stderr.strip())
        absolute = {os.path.abspath(p): p for p in paths}
        records = []
        for line in proc.stdout.splitlines():
            record = json.loads(line)
            record["path"] = absolute.get(record["path"], record["path"])
            records.append(record)
        return records
