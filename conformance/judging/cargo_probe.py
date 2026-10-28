"""CargoProbe: what this machine has for the Rust targets."""

import shutil


class CargoProbe:
    """Says if there is a ``cargo`` to build and run the Rust runner."""

    def present(self) -> bool:
        return shutil.which("cargo") is not None
