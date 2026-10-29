"""``python -m codeupipe_add <kind> <name> [dir] [--description TEXT]``

Makes the component file and the test file of one component, in the
directory where it runs (conformance/ADD.md). Prints each file that it made.

Exit code: 0 the files are made, 1 a file exists (nothing is written), 2 the
arguments cannot be used (nothing is written).
"""

import argparse
import os
import sys

from codeupipe import Payload

from .add_pipeline import AddPipeline
from .refusal import Refusal


# cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="codeupipe add",
                                     description="Make the files of a component (conformance/ADD.md).")
    parser.add_argument("kind", help="filter, predicate, tap, hook or pipeline")
    parser.add_argument("name", help="the name of the component: Discount, at_least or audit-log")
    parser.add_argument("dir", nargs="?", default=".", help="the directory of the component file (default: .)")
    parser.add_argument("--description", default="", help="what the component does, for its header comment")
    args = parser.parse_args(argv)
    try:
        out = AddPipeline().run(Payload({"root": os.getcwd(), "kind": args.kind, "name": args.name,
                                         "directory": args.dir, "description": args.description}))
    except Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return refusal.exit_code
    for path in out.get("written"):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
