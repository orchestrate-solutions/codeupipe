"""DefaultTargetsFilter: each target that this machine can run."""

from codeupipe import Payload


class DefaultTargetsFilter:
    """Filter (sync).

    Input keys: ``targets`` ({name: how to start its runner}), ``needs``
    ({name: paths that must exist for the target}).
    Output keys: ``names``. A Python target always runs. A TypeScript target
    needs a Node that runs ``.ts`` files, and the paths of ``needs``.

    ``node_runs_typescript`` is a function with no arguments that says if
    the machine has such a Node.
    """

    def __init__(self, node_runs_typescript):
        self.node_runs_typescript = node_runs_typescript

    def call(self, payload: Payload) -> Payload:
        return payload.insert("names", self.choose(payload.get("targets"), payload.get("needs", {})))

    def choose(self, targets, needs) -> list:
        return [name for name in targets if self.can_run(name, needs)]

    def can_run(self, name, needs) -> bool:
        if not name.startswith("typescript:"):
            return True
        return self.node_runs_typescript() and all(path.exists() for path in needs.get(name, []))
