"""NodeProbe: what this machine has for the TypeScript targets."""

import shutil
import subprocess


# cup: allow-plain the edge to the machine: it asks which Node is installed
class NodeProbe:
    """Says if there is a Node that runs a ``.ts`` file as it is (22.18 or later)."""

    def runs_typescript(self) -> bool:
        node = shutil.which("node")
        if node is None:
            return False
        try:
            version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout
            major, minor = (int(part) for part in version.strip().lstrip("v").split(".")[:2])
        except (OSError, ValueError, subprocess.SubprocessError):
            return False
        return (major, minor) >= (22, 18)
