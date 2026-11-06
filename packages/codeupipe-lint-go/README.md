# codeupipe-lint for Go

A linter for Go code that uses codeupipe. It reads the source and does not
run it.

The linter is a codeupipe pipeline: [lint_pipeline.go](lint_pipeline.go).
Its steps carry a type of their own, `*LintRun`, in place of a `Payload`,
because a run holds syntax trees. It has no dependencies: Go's own
`go/parser` and `go/ast` read the source, and `encoding/json` reads the
config file.

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible. No version is tagged yet. Use it
from the main branch:

```bash
go install github.com/orchestrate-solutions/codeupipe/packages/codeupipe-lint-go/codeupipe-lint@main
```

It needs Go 1.22 or later. It is a tool for the developer: a project that
uses codeupipe does not need it to build or to run.

```bash
codeupipe-lint .                        # files or directories
codeupipe-lint --exclude '*/generated/*' .
codeupipe-lint --disable CUP-I005 .
codeupipe-lint --strict .               # a warning fails the run too
codeupipe-lint --rules                  # list the rule ids
codeupipe-lint                          # paths come from cup.config.json
```

Each finding is one line, and the message names the fix:

```
path:line:col  CUP-A005 unnamed-pipeline-step  Step `codeupipe.NewPipeline()` is a plain Pipeline, nested as a step. A nested pipeline must be (...)
```

Exit code: **0** no findings, **1** findings, **2** a path could not be
read or the arguments cannot be used.

From Go: `codeupipelint.LintPaths(paths, codeupipelint.LintOptions{Exclude, Disable, Strict})`
returns the `*LintRun` (`Findings`, `Suppressed`, `Errors`, `Report`,
`ExitCode`).

## Rules

The ids are those of the Python, TypeScript and Rust linters.

| id | slug | what |
|---|---|---|
| CUP-I000 | parse-error | the file has a syntax error |
| CUP-A001 | function-step | a step that is a conversion to a function type: `AddFilter(FilterFunc(fn))` |
| CUP-A003 | local-type-step | a composite literal of a type that is declared in a function, or of an anonymous struct type |
| CUP-A005 | unnamed-pipeline-step | a plain `NewPipeline()` or `NewPipelineOf[T]()` nested as a step |
| CUP-A008 | function-predicate | a Valve predicate that is a conversion to a function type |
| CUP-I003 | state-read-in-step | a Filter (`Call`) or a Predicate (`Test`) reads the State of a pipeline |
| CUP-I004 | write-outside-filter | a Tap, a Predicate or a Hook writes to its payload |
| CUP-I005 | one-primitive-per-file | a second primitive at the top level of a file |
| CUP-I006 | primitive-file-name | the file name is not the type name in snake_case |
| CUP-I007 | primitive-role-suffix | the type name does not end with its role |
| CUP-I008 | logic-outside-primitive | **a warning.** A function, a method of a type that is not a primitive, or a top-level `var` has logic (`if`, `switch`, `select`, a loop, `goto`) |
| CUP-I009 | marker-allows-nothing | **a warning.** A `cup: allow-...` comment that allowed no finding |

A step is the argument of `AddFilter`, `AddTap` or `AddPipeline` (on any
receiver), and the two arguments of `AddValve(predicate, filter)`.

A type is a primitive when the same file has one of its step methods, with
the shape of the interface: `Call` (Filter), `Test` (Predicate), `Observe`
(Tap), `Before`, `After` or `OnError` (Hook), or `AddSteps` (Pipeline). A
struct that embeds `codeupipe.HookBase` is a Hook.

**CUP-I004 is a rule of the linter in Go**, as in Python and TypeScript. Go
has no pointer that only reads, so a Tap, a Predicate and a Hook get the same
`*Payload` as a Filter. The rule flags a call of `Insert`, `Remove`, `Merge`,
`WithTrace` or `Stamp` on the payload parameter, and an assignment through it
(`order.Bulk = true`, `*order = Order{}`) for a type of your own. An
assignment to the parameter itself (`payload = payload.Copy()`) changes only
the local variable, so it is not a write.

## Rules that the compiler checks

The types of the Go runtime refuse these, so the linter has no rule for
them:

| id | In Go |
|---|---|
| CUP-A002 | A function is not a step: it has no `Call`, `Test` or `Observe` method |
| CUP-A009 | An object literal does not exist in Go. An anonymous struct that embeds a step is a step, and CUP-A003 flags it |
| CUP-I001 | The data of a Payload is in unexported fields |

A `--disable` or a `lint.disable` with one of these ids is an error, as for
any id the linter does not have.

## Logic that is not in a primitive (CUP-I008)

A project that uses codeupipe writes its logic as Filters, Predicates, Taps,
Hooks and Pipelines. Logic in a plain function or a plain type works as
well, so nothing else shows the mistake. This rule shows it.

- **It is a warning.** It is in the report and it is counted apart
  (`No findings. 3 warnings.`). It does not make the exit code 1. With
  `--strict`, a warning fails the run as a finding does.
- **Flagged, once each:** a top-level function (`main` and `init` too), a
  method of a type that is not a primitive of the file, and the first
  top-level `var` whose value has logic. Logic in a function literal counts
  for the function around it.
- **Not flagged:** a method of a primitive (so a helper method of a Filter is
  fine), code with no logic, and a `_test.go` file.
- **Not seen:** `&&`, `||`, and a loop in a method call.
- For logic that must be plain code (the edge to a file or a server, the
  entry of a program), say why in a comment: `// cup: allow-plain <reason>`.

## Turn a finding off

- **One line.** A comment on the line of the finding, on the line of the
  `Add...` call around it, or alone on the line directly above:
  `// cup: allow-anonymous` for a CUP-A finding;
  `// cup: allow-state-read`, `allow-shared-file`, `allow-name` or
  `allow-plain` for a CUP-I finding. Any text can follow the marker. A
  finding of a function or a type is on the line of its name, so the comment
  is the last line of its doc comment:

  ```go
  // ReadConfig reads the config file.
  // cup: allow-plain the edge of the program: it reads a file before the pipeline runs
  func ReadConfig(path string) (*Config, error) {
  ```

  A comment that allows no finding is itself a finding (CUP-I009), so an
  old one does not stay. Text in a string is not a marker.
- **Files.** `--exclude GLOB`, or `lint.exclude` in the config file. In a
  glob, `*` is any text, a `/` too.
- **A rule, for the project.** `--disable RULE`, or `lint.disable` in the
  config file. A rule id that does not exist is an error.

## Config file

`cup.config.json`, in the directory that the command runs from, or the file
of `--config`. The linter reads the `lint` section and no other.

```json
{"lint": {"paths": ["."], "exclude": ["*/generated/*"], "disable": ["CUP-I005"]}}
```

The file is used only when no paths are given on the command line. A key in
`lint` that the linter does not read is an error.

## Limits

- A name is followed to the `:=`, `=` or `var` that gave its value, in the
  same function, before the call; the last one wins. A parameter, a name
  from another function, a name that a function literal takes from the
  function around it, and the result of a call are not followed.
- A type is matched by its name in the file. The linter reads syntax only:
  it does not resolve imports or types. So a method in another file of the
  package does not make its type a primitive in this file.
- CUP-I003 flags each `E.State()` with no arguments, and each use of a
  field of the receiver whose type is `State` or `*State`.
- CUP-I004 follows the payload parameter by its name only: a copy of the
  pointer (`q := payload`) is not followed.
- As the `go` command does, the linter skips the directories `testdata` and
  `vendor`, and each directory whose name starts with `.` or `_`.
- `_test.go` files are not checked by CUP-I005, I006, I007 and I008.

## Development

The linter is a Go module of its own. Its `go.mod` points at the runtime of
this repository with a `replace`, so it builds with no download. In this
directory:

```bash
go test -race ./...  # the tests
go vet ./...
gofmt -l .
go run ./codeupipe-lint --strict . ../codeupipe-go ../../conformance/runners/go
```

## License

Apache License 2.0.
