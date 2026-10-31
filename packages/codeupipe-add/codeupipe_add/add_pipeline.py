"""AddPipeline: ``codeupipe add``, built as a codeupipe pipeline.

Steps:
    1. TypeNameFilter        kind and name -> DiscountFilter, discount_filter
    2. PlanFilesFilter       the paths of the two files, and the import path
    3. RefuseExistingFilter  a file that exists stops the run (exit 1)
    4. RenderFilesFilter     the text of the two files
    5. WriteFilesFilter      the files, on disk
"""

from codeupipe import Pipeline

from .plan_files_filter import PlanFilesFilter
from .refuse_existing_filter import RefuseExistingFilter
from .render_files_filter import RenderFilesFilter
from .type_name_filter import TypeNameFilter
from .write_files_filter import WriteFilesFilter


class AddPipeline(Pipeline):
    """Input keys: ``root``, ``kind``, ``name``, ``directory``, ``description``.
    Output keys: ``written``. A step that cannot go on raises Refusal."""

    def __init__(self):
        super().__init__()
        self.add_filter(TypeNameFilter())
        self.add_filter(PlanFilesFilter())
        self.add_filter(RefuseExistingFilter())
        self.add_filter(RenderFilesFilter())
        self.add_filter(WriteFilesFilter())
