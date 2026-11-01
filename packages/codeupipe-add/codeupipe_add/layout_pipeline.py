"""LayoutPipeline: ``codeupipe add --layout``, built as a codeupipe pipeline.

Steps:
    1. ReadLayoutFilter      the file -> the layout, as data
    2. CheckLayoutFilter     the keys, and the shape of each value
    3. NameComponentsFilter  the names and paths of phase 1, for each component
    4. ResolveStepsFilter    the calls and imports of each pipeline
    5. RenderLayoutFilter    the text of each file
    6. WriteLayoutFilter     the files that are not there yet, on disk
    7. StalePipelinesFilter  each kept pipeline whose steps the layout changed

Steps 1 to 5 check the whole layout, so a refusal writes nothing.
"""

from codeupipe import Pipeline

from .check_layout_filter import CheckLayoutFilter
from .name_components_filter import NameComponentsFilter
from .read_layout_filter import ReadLayoutFilter
from .render_layout_filter import RenderLayoutFilter
from .resolve_steps_filter import ResolveStepsFilter
from .stale_pipelines_filter import StalePipelinesFilter
from .write_layout_filter import WriteLayoutFilter


class LayoutPipeline(Pipeline):
    """Input keys: ``root``, ``layout_path``.
    Output keys: ``written``, ``kept``, ``stale``. A step that cannot go on raises Refusal."""

    def __init__(self):
        super().__init__()
        self.add_filter(ReadLayoutFilter())
        self.add_filter(CheckLayoutFilter())
        self.add_filter(NameComponentsFilter())
        self.add_filter(ResolveStepsFilter())
        self.add_filter(RenderLayoutFilter())
        self.add_filter(WriteLayoutFilter())
        self.add_filter(StalePipelinesFilter())
