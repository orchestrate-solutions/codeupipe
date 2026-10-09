"""Reference steps for the conformance vocabulary (conformance/README.md).

Ordinary CUP components configured through their constructors, so the
static targets exercise constructor-config baking as well as lowering. One
step in each file.
"""

from .add import Add
from .append import Append
from .copy import Copy
from .fail import Fail
from .fail_tap import FailTap
from .has import Has
from .merge import Merge
from .mutate import Mutate
from .nested import Nested
from .noop_hook import NoopHook
from .noop_tap import NoopTap
from .record_hook import RecordHook
from .record_tap import RecordTap
from .remove import Remove
from .set import Set

__all__ = [
    "Add",
    "Append",
    "Copy",
    "Fail",
    "FailTap",
    "Has",
    "Merge",
    "Mutate",
    "Nested",
    "NoopHook",
    "NoopTap",
    "RecordHook",
    "RecordTap",
    "Remove",
    "Set",
]
