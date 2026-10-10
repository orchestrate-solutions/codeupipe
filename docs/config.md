# cup.config.json

One optional file, in the directory the tools are run from. It holds what
Lint and Compile would otherwise be told on the command line, so that a
person, CI or an agent can run them with no arguments and get the same run
every time.

```json
{
  "lint": {
    "paths": ["src"],
    "exclude": ["*/generated/*"],
    "disable": ["CUP-I005"]
  },
  "compile": [
    {"target": "app.pipelines:checkout", "out": "build/checkout"},
    {"target": "app.pipelines:refund", "out": "build/refund", "lowering": "inline"}
  ]
}
```

```bash
python -m codeupipe_lint.invariants          # lint.paths, minus lint.exclude
python -m codeupipe_lint.anonymous_steps     # the same
python -m codeupipe.compile          # every pipeline under compile
```

## Keys

| Key | Read by | Meaning |
|---|---|---|
| `lint.paths` | both linters | files or directories to check |
| `lint.exclude` | both linters | fnmatch globs for files to skip |
| `lint.disable` | both linters | rule ids to switch off for the whole project |
| `compile[].target` | Compile | the pipeline, as `module:name` |
| `compile[].out` | Compile | the directory to write its package into |
| `compile[].lowering` | Compile | `steps` (default) or `inline` |
| `compile[].observe` | Compile | `true` to keep State and Hooks (steps only) |

That is all of them.

## Rules

- **The command line wins.** Give paths to a linter, or a target to Compile,
  and the file is not used for that run at all: a file someone names is
  checked even if `lint.exclude` would skip it. With no paths, `--exclude` on
  the command line replaces `lint.exclude`, and `--disable` replaces
  `lint.disable`.
- **A key no tool reads is an error.** So is a wrong value. The message names
  the key and the keys there are. A setting that does nothing cannot sit in
  the file.
- **The file is optional.** With no file the tools behave as before and need
  their arguments.
- `--config FILE` reads another file. Unlike the default, a named file that
  does not exist is an error.
- Compile tries every pipeline listed and exits with the worst result: 1 if
  one was refused, 2 if one could not be run.

## Adding a key

Add it when a tool in this repo reads it, with a test, and not before. Tools
built on CUP keep their settings in their own files.

This repo's own file, [cup.config.json](../cup.config.json), lists what its
linters check.
