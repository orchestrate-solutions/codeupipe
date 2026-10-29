"""``python -m codeupipe_add <kind> <name> [dir] [--description TEXT]``
``python -m codeupipe_add --layout cup.layout.yaml``

Makes the component file and the test file of one component, or of each
component of a layout, in the directory where it runs (conformance/ADD.md).
Prints each file that it made.

Exit code: 0 the files are made, 1 a file exists (nothing is written), 2 the
arguments cannot be used (nothing is written). With --layout, a file that
exists is kept, and the exit code is 0.
"""

import argparse
import os
import sys

from codeupipe import Payload

from .add_pipeline import AddPipeline
from .layout_pipeline import LayoutPipeline
from .refusal import Refusal


# cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
def main(argv=None) -> int:
    # allow_abbrev=False: --desc is not read as --description, as in the other languages.
    parser = argparse.ArgumentParser(prog="codeupipe add", allow_abbrev=False,
                                     usage="codeupipe add <kind> <name> [dir] [--description TEXT]\n"
                                           "       codeupipe add --layout FILE",
                                     description="Make the files of a component, or of each component of a "
                                                 "layout (conformance/ADD.md).")
    parser.add_argument("kind", nargs="?", help="filter, predicate, tap, hook or pipeline")
    parser.add_argument("name", nargs="?", help="the name of the component: Discount, at_least or audit-log")
    parser.add_argument("dir", nargs="?", help="the directory of the component file (default: .)")
    parser.add_argument("--description", help="what the component does, for its header comment")
    parser.add_argument("--layout", help="a YAML (or JSON) file of components and pipelines")
    args = parser.parse_args(argv)
    if args.layout is not None:
        if args.kind is not None or args.description is not None:
            parser.error("--layout takes no kind, name, dir or --description: they are in the layout.")
        run = LayoutPipeline(), {"layout_path": args.layout}
    elif args.name is None:
        parser.error("the kind and the name are required, or --layout FILE.")
    else:
        run = AddPipeline(), {"kind": args.kind, "name": args.name, "directory": args.dir or ".",
                              "description": args.description or ""}
    pipeline, given = run
    try:
        out = pipeline.run(Payload(dict(given, root=os.getcwd())))
    except Refusal as refusal:
        print(str(refusal), file=sys.stderr)
        return refusal.exit_code
    stale = out.get("stale") or []
    for path in out.get("kept") or []:
        if path in stale:
            print("%s exists, kept, and its steps are not those of the layout. Change the file: the command does "
                  "not write it again." % path, file=sys.stderr)
        else:
            print("%s exists, kept" % path, file=sys.stderr)
    for path in out.get("written"):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
