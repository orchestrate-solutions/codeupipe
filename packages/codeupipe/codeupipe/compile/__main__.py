"""``python -m codeupipe.compile [module:name --out DIR] [--lowering steps|inline] [--observe] [--overwrite] [--config FILE]``

Export a Pipeline to plain Python with no framework import (docs/compile.md).
With no ``module:name``, every pipeline listed under ``compile`` in
``cup.config.json`` is exported (packages/codeupipe/codeupipe/config.py).

Exit code: 0 exported, 1 a pipeline has a shape the export refuses, 2 the
command could not run (bad target, bad options, output directory in use, a
config that cannot be used).
"""

import argparse
import sys
from pathlib import Path

from codeupipe.config import DEFAULT_NAME, ConfigError, load_config
from codeupipe.core import Payload

from .errors import UnsupportedFilterShape
from .pipelines.export_pipeline import build_export_pipeline_v2
from .resolve_target import TargetError, resolve_target


def _usage_error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


# cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
def export(target: str, out_dir: str, lowering: str = "steps", observe: bool = False, overwrite: bool = False) -> int:
    """Export one pipeline; the exit code for it."""
    if observe and lowering == "inline":
        return _usage_error("--observe needs the steps layout; drop --lowering inline")
    try:
        pipeline = resolve_target(target)
    except TargetError as error:
        return _usage_error(str(error))
    out = Path(out_dir)
    if out.exists() and not out.is_dir():
        return _usage_error(f"{out} is not a directory")
    if out.is_dir() and any(out.iterdir()) and not overwrite:
        return _usage_error(f"{out} is not empty; choose another directory or pass --overwrite")

    try:
        result = build_export_pipeline_v2(write=False).run(Payload({
            "pipeline": pipeline, "lowering": lowering, "observe": observe,
        }))
    except UnsupportedFilterShape as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1

    # Written here, not by the export's Tap: a Tap failure never halts a run,
    # so a failed write would otherwise look like a successful export.
    for file in result.get("files") or []:
        path = out / file["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file["content"], encoding="utf-8")
        print(path)
    return 0


# cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m codeupipe.compile",
                                     description="Export a Pipeline to plain Python (docs/compile.md).")
    parser.add_argument("target", nargs="?",
                        help="the pipeline, as module:name (a Pipeline, a builder function, or a Pipeline type); "
                             "omit it to export every pipeline in the config")
    parser.add_argument("--out", metavar="DIR", help="directory to write the package into")
    parser.add_argument("--lowering", choices=["steps", "inline"], default="steps",
                        help="steps: one module per step (default). inline: one flat run(), fastest")
    parser.add_argument("--observe", action="store_true",
                        help="also record State and call Hooks, as the dynamic run does (steps layout only)")
    parser.add_argument("--overwrite", action="store_true", help="write into DIR even if it is not empty")
    parser.add_argument("--config", metavar="FILE", help="read the pipelines to export from FILE, not %s" % DEFAULT_NAME)
    args = parser.parse_args(argv)

    if args.target:
        if not args.out:
            return _usage_error("--out DIR is needed with a target")
        return export(args.target, args.out, args.lowering, args.observe, args.overwrite)
    try:
        pipelines = (load_config(args.config) or {}).get("compile", [])
    except ConfigError as error:
        return _usage_error(str(error))
    if not pipelines:
        return _usage_error("give a target and --out, or list pipelines under compile in %s" % DEFAULT_NAME)
    # Every pipeline is tried; the worst exit code is the command's.
    return max(export(pipeline["target"], pipeline["out"], pipeline.get("lowering", "steps"),
                      pipeline.get("observe", False), args.overwrite) for pipeline in pipelines)


if __name__ == "__main__":
    sys.exit(main())
