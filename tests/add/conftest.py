import pathlib
import sys

# The package is not installed for the tests of this repository; it is read from its directory.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "packages" / "codeupipe-add"))
