"""Reference steps for the conformance vocabulary (conformance/README.md).

Ordinary CUP components configured through their constructors, so the
static targets exercise constructor-config baking as well as lowering. One
step in each file.
"""

from .add_filter import AddFilter
from .append_filter import AppendFilter
from .copy_filter import CopyFilter
from .fail_filter import FailFilter
from .fail_tap import FailTap
from .has_filter import HasFilter
from .merge_filter import MergeFilter
from .mutate_filter import MutateFilter
from .nested_pipeline import NestedPipeline
from .noop_hook import NoopHook
from .noop_tap import NoopTap
from .record_hook import RecordHook
from .record_tap import RecordTap
from .remove_filter import RemoveFilter
from .set_filter import SetFilter

__all__ = [
    "AddFilter",
    "AppendFilter",
    "CopyFilter",
    "FailFilter",
    "FailTap",
    "HasFilter",
    "MergeFilter",
    "MutateFilter",
    "NestedPipeline",
    "NoopHook",
    "NoopTap",
    "RecordHook",
    "RecordTap",
    "RemoveFilter",
    "SetFilter",
]
