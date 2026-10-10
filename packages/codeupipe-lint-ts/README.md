# codeupipe-lint for TypeScript

A linter for TypeScript code that uses codeupipe. It reads the source and
does not run it.

The linter is a codeupipe pipeline: [src/lint-pipeline.ts](src/lint-pipeline.ts).
It depends on `codeupipe` and on the `typescript` package, which it uses to
parse the files.

```bash
npm install --save-dev codeupipe-lint
```

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible.

```bash
npx codeupipe-lint src                  # files or directories
npx codeupipe-lint --exclude '*/generated/*' src
npx codeupipe-lint --disable CUP-I005 src
npx codeupipe-lint --rules              # list the rule ids
npx codeupipe-lint                      # paths come from cup.config.json
```

Each finding is one line, and the message names the fix:

```
path:line:col  CUP-A001 lambda-step  Filter is a function. Define it at module level as a named class (...)
```

Exit code: **0** no findings, **1** findings, **2** a path could not be
read or the arguments cannot be used.

From TypeScript: `lintPaths(paths, { exclude, disable })` returns the result
Payload (`findings`, `suppressed`, `errors`, `report`, `exitCode`).

## Rules

The ids are those of the Python linter, where it has the rule.

| id | slug | what |
|---|---|---|
| CUP-I000 | parse-error | the file has a syntax error |
| CUP-A001 | lambda-step | an arrow function or a function expression as a step |
| CUP-A002 | local-function-step | a named function as a Filter or a Tap |
| CUP-A003 | local-type-step | an instance of a class that is declared in a function, or of a class with no name |
| CUP-A005 | unnamed-pipeline-step | a plain `new Pipeline()` nested as a step |
| CUP-A008 | function-predicate | a named function as a Valve predicate |
| CUP-A009 | object-literal-step | an object literal as a step. TypeScript only |
| CUP-I003 | state-read-in-step | a Filter (`call`) or a Predicate (`test`) reads the State of a pipeline |
| CUP-I004 | write-outside-filter | a Tap, a Predicate or a Hook writes to the Payload |
| CUP-I005 | one-primitive-per-file | a second primitive class at the top level of a file |
| CUP-I006 | primitive-file-name | the file name is not the class name in kebab-case |
| CUP-I007 | primitive-role-suffix | the class name does not end with its role |

A step is the argument of `addFilter`, `addTap` or `addPipeline` (on any
receiver), and the two arguments of `addValve(predicate, filter)`.

A class is a primitive by its shape: `extends Pipeline`, `extends Hook`,
`implements Filter`, `implements Tap`, `implements Predicate`, or a method
`call`, `observe` or `test` with exactly one required parameter.

## Rules of the Python linter that are not here

- **CUP-I001** (a change to the Payload behind its API). The data of a
  Payload is in a private field (`#data`), so the language refuses this.
- **CUP-I002** (a change to a value that Payloads share). Not built yet.

## Turn a finding off

- **One line.** A comment on the line of the finding, on the line of the
  `add...` call around it, or alone on the line directly above:
  `// cup: allow-anonymous` for a CUP-A finding;
  `// cup: allow-state-read`, `allow-outside-write`, `allow-shared-file` or
  `allow-name` for a CUP-I finding. Any text can follow the marker.
- **Files.** `--exclude GLOB`, or `lint.exclude` in the config file. In a
  glob, `*` is any text, a `/` too.
- **A rule, for the project.** `--disable RULE`, or `lint.disable` in the
  config file. A rule id that does not exist is an error.

## Config file

`cup.config.json`, in the directory that the command runs from. The linter
reads the `lint` section and no other.

```json
{"lint": {"paths": ["src"], "exclude": ["*/generated/*"], "disable": ["CUP-I005"]}}
```

The file is used only when no paths are given on the command line. A key in
`lint` that the linter does not read is an error.

## Limits

- A name is followed to its declaration in the same file when that is a
  `const`, a function or a class. A `let`, a parameter, an import and the
  result of a call are not followed, so a function that returns an anonymous
  step is not seen.
- The linter reads syntax only. It does not use the types of the program.
- Test files (`*.test.ts`, `*.spec.ts`, and files under `tests/`) are not
  checked by CUP-I005, CUP-I006 and CUP-I007.

## Development

The three TypeScript packages are one npm workspace. Run `npm ci` once, at
the root of the repository. Then, in this directory:

```bash
npm test             # builds the core package first, then runs the tests
npm run typecheck
npm run build        # JavaScript and type files in dist/
npm run lint         # the linter on its own source, the core package and the conformance runner
```

## License

Apache License 2.0.
