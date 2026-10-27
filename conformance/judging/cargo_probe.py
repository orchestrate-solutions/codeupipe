"""CargoProbe: what this machine has for the Rust targets."""

import shutil


# cup: allow-plain the edge to the machine: it asks whether cargo is installed
class CargoProbe:
    """Says if there is a ``cargo`` to build and run the Rust runner."""

    def present(self) -> bool:
        return shutil.which("cargo") is not None
