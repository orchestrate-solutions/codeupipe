"""The errors that say "this target cannot express this case"."""


class Unsupported(Exception):
    """The target cannot express the case. The message is the reason."""


class ExportRefused(Unsupported):
    """The compiler refused the pipeline of the case."""
