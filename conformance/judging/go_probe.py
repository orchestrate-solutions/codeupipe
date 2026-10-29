"""GoProbe: what this machine has for the Go targets."""

import shutil


class GoProbe:
    """Says if there is a ``go`` to build and run the Go runner."""

    def present(self) -> bool:
        return shutil.which("go") is not None
