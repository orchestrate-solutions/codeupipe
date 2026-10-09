"""``python -m codeupipe_lint.invariants [--exclude GLOB] [--config FILE] [--rules] [paths...]``

With no paths, they come from ``cup.config.json`` (packages/codeupipe/codeupipe/config.py).

Exit code: 0 clean, 1 invariant violations found, 2 a path could not be read
or the config cannot be used.
"""

import argparse
import sys

from codeupipe.config import DEFAULT_NAME, ConfigError, load_config

from .lint_pipeline import lint_paths
from .rules import RULES
from ..rule_ids import unknown_rules


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m codeupipe_lint.invariants",
                                     description="Enforce CUP's structural invariants (packages/codeupipe-lint/README.md).")
    parser.add_argument("paths", nargs="*", help="files or directories to check")
    parser.add_argument("--exclude", action="append", metavar="GLOB",
                        help="skip files whose path matches this fnmatch glob (repeatable)")
    parser.add_argument("--disable", action="append", metavar="RULE",
                        help="switch this rule off (repeatable), e.g. CUP-I005")
    parser.add_argument("--config", metavar="FILE", help="read paths and excludes from FILE, not %s" % DEFAULT_NAME)
    parser.add_argument("--rules", action="store_true", help="list the rule ids and exit")
    args = parser.parse_args(argv)
    if args.rules:
        for rule, slug in sorted(RULES.items()):
            print("%s  %s" % (rule, slug))
        return 0
    paths, exclude, disable = args.paths, args.exclude, args.disable
    if not paths:
        # The file stands in for the arguments only when no paths are given:
        # a path someone names is checked, whatever the file excludes.
        try:
            lint = (load_config(args.config) or {}).get("lint", {})
        except ConfigError as error:
            print("error: %s" % error, file=sys.stderr)
            return 2
        paths, exclude = lint.get("paths"), args.exclude or lint.get("exclude")
        disable = args.disable or lint.get("disable")
    if not paths:
        parser.error("give at least one path, or list them under lint.paths in %s" % DEFAULT_NAME)
    unknown = unknown_rules(disable or ())
    if unknown:
        print("error: no such rule: %s (the rules are listed by --rules of each linter)" % ", ".join(unknown),
              file=sys.stderr)
        return 2
    out = lint_paths(paths, exclude, disable)
    print(out.get("report"))
    if out.get("error_report"):
        print(out.get("error_report"), file=sys.stderr)
    return out.get("exit_code")


if __name__ == "__main__":
    sys.exit(main())
