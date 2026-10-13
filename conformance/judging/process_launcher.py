"""ProcessLauncher: starts the runner of one target and reads what it reports."""

import json
import os
import subprocess


# cup: allow-plain the edge to the runners: it starts a process, gives it the cases and reads its report
class ProcessLauncher:
    """Runs one target. ``spec`` has ``cmd``, ``env`` and ``cwd``.

    Gives ``(results, None)``, with ``results`` as {case id: result}, or
    ``(None, reason)`` when the runner did not end well or its output
    cannot be read.
    """

    def run(self, spec, cases):
        env = dict(os.environ)
        env.update(spec["env"])
        proc = subprocess.run(
            spec["cmd"], input=json.dumps(cases), capture_output=True, text=True,
            cwd=spec["cwd"], env=env, timeout=600,
        )
        if proc.returncode != 0:
            return None, f"runner exited {proc.returncode}: {proc.stderr.strip()[-2000:]}"
        try:
            return {r["id"]: r for r in json.loads(proc.stdout)}, None
        except (json.JSONDecodeError, KeyError) as error:
            return None, f"unreadable runner output ({error}): {proc.stdout[:500]}"
