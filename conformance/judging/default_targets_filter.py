"""DefaultTargetsFilter: each target that this machine can run."""

from codeupipe import Payload


class DefaultTargetsFilter:
    """Filter (sync).

    Input keys: ``targets`` ({name: how to start its runner}), ``needs``
    ({name: paths that must exist for the target}).
    Output keys: ``names``. A Python target always runs. A TypeScript target
    needs a Node that runs ``.ts`` files, and the paths of ``needs``. A Rust
    target needs ``cargo``.

    ``node_runs_typescript`` and ``has_cargo`` are functions with no
    arguments that say if the machine has such a Node, and a ``cargo``.
    """

    def __init__(self, node_runs_typescript, has_cargo=lambda: False):
        self.node_runs_typescript = node_runs_typescript
        self.has_cargo = has_cargo

    def call(self, payload: Payload) -> Payload:
        return payload.insert("names", self.choose(payload.get("targets"), payload.get("needs", {})))

    def choose(self, targets, needs) -> list:
        return [name for name in targets if self.can_run(name, needs)]

    def can_run(self, name, needs) -> bool:
        if name.startswith("rust:"):
            return self.has_cargo()
        if not name.startswith("typescript:"):
            return True
        return self.node_runs_typescript() and all(path.exists() for path in needs.get(name, []))
