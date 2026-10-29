# The `add` contract

This document defines `codeupipe add`, the command that adds components to
a project: their files, their tests, and the pipelines that join them. Where
`cup` is installed, `cup add` is the same command.

The command is in each runtime: Python, TypeScript, Rust and Go. Each one
writes files in its own language. Each one follows this contract, and the
same cases ([add/cases.json](add/cases.json)) judge each one, as the cases of
[API.md](API.md) judge the runtimes.

There are two phases:

1. **One component.** `codeupipe add filter Discount` makes one component
   file and one test file.
2. **A layout.** `codeupipe add --layout cup.layout.yaml` makes all the
   components in a YAML file, and the pipelines that join them. The file
   stays in the project, as a record of its structure.

Both are `add`: one component, or many from a file. The word is that of
`add_filter` in the code, and of tools that add a part to a project.

Phase 1 comes first. Phase 2 starts when each runtime passes the phase 1
cases.

## Principles

1. **The output passes the linter.** The files are correct when they are
   made: the file name, the role suffix, one primitive in each file. The
   linter of the language finds nothing in them, in strict mode. This is the
   main rule.
2. **The component is valid and does nothing.** It compiles (or it imports),
   and it does not change the data.
3. **The test fails.** The test file runs, and its one test fails with a
   known message. The work starts at RED.
4. **A file is never overwritten.** If a file exists, the command writes
   nothing.
5. **The command adds no dependency.** Phase 1 uses only the standard
   library of the language and the runtime package.

## Phase 1: one component

### The command

```
codeupipe add <kind> <name> [dir] [--description TEXT]
```

| Argument | Meaning |
|---|---|
| `kind` | `filter`, `predicate`, `tap`, `hook` or `pipeline` |
| `name` | The name of the component. See "Names" |
| `dir` | The directory of the component file. It is relative to the directory where the command runs, which is the root of the project. The default is `.`, and `src` for Rust |
| `--description TEXT` | One or more sentences that say what the component does. They go in the header comment |

The other primitives are not made with `add`:

| Primitive | Why |
|---|---|
| Payload, State | The runtime makes them. A user does not write one |
| Valve | It is a call, not a type: `add_valve(predicate, filter)`. Make the Predicate and the Filter |

A type of your own (API.md, "A type of your own") is not in phase 1.

### Names

The command makes the type name from `name`:

1. **Words.** `name` can be PascalCase (`AtLeast`), snake_case (`at_least`) or
   kebab-case (`at-least`). Each `_` and `-` starts a new word, and the first
   letter of each word becomes a capital: `at_least` gives `AtLeast`. A name
   that is PascalCase already does not change.
2. **The role suffix.** If the name does not end with the role of its kind
   (`Filter`, `Predicate`, `Tap`, `Hook`, `Pipeline`), the role is added:
   `filter Discount` gives `DiscountFilter`. `filter DiscountFilter` also
   gives `DiscountFilter`.
3. **The file name** comes from the type name, by the rule of the linters
   (CUP-I006). A word starts before a capital that follows a small letter or
   a digit, and before a capital that is followed by a small letter and
   follows a capital. As a regular expression:
   `(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])`. The words are joined with
   `_` (Python, Rust, Go) or `-` (TypeScript), in small letters:
   `HTTPGetFilter` gives `http_get_filter` and `http-get-filter`.

A name is refused (exit 2) if it is empty, if it does not start with a
letter, or if it has a character that is not a letter, a digit, `_` or `-`.

### The files

The command runs in the root of the project. It makes two files:

| Language | Component | Test |
|---|---|---|
| Python | `<dir>/discount_filter.py` | `tests/test_discount_filter.py` |
| TypeScript | `<dir>/discount-filter.ts` | `tests/discount-filter.test.ts` |
| Rust | `<dir>/discount_filter.rs` | `tests/discount_filter.rs` |
| Go | `<dir>/discount_filter.go` | `<dir>/discount_filter_test.go` |

Go keeps a test beside its source; that is the rule of the language. The
other languages keep the tests in `tests/` at the root, as this repository
does. The command makes a directory that does not exist.

### What the component file has

- **A header comment** with the description, or, with no `--description`,
  the text `TODO: say what <TypeName> does.`
- **One type**, with the role suffix, which implements its role:

| Kind | What it does |
|---|---|
| `filter` | Returns the Payload with no change |
| `predicate` | Returns false |
| `tap` | Does nothing |
| `hook` | Does nothing at each event |
| `pipeline` | A named pipeline with no steps |

- **Nothing else.** No settings, no helper functions, and no example code
  that a user must delete.

Each runtime writes the type in its own form, as its README shows:

| | Filter | Pipeline |
|---|---|---|
| Python | `class DiscountFilter:` with `call(self, payload)` | `class PricingPipeline(Pipeline):` |
| TypeScript | `export class DiscountFilter implements Filter` | `export class PricingPipeline extends Pipeline` |
| Rust | `pub struct DiscountFilter;` and `impl Filter for DiscountFilter` | `pub struct PricingPipeline;` and `impl NamedPipeline for PricingPipeline` |
| Go | `type DiscountFilter struct{}` with `Call(ctx, payload)` | `type PricingPipeline struct{}` with `AddSteps(pipeline)` |

### What the test file has

One test, which makes the component and then fails with this message:

```
Write the acceptance case for DiscountFilter.
```

The test imports the component the way that a user's test would:

| Language | Import |
|---|---|
| Python | The module path of `<dir>`, with `.` between the parts: `from src.pricing.discount_filter import DiscountFilter`. With `dir` `.`, `from discount_filter import DiscountFilter` |
| TypeScript | The relative path from `tests/`, with the `.ts` extension: `import { DiscountFilter } from "../src/pricing/discount-filter.ts"` |
| Rust | The crate, by its name in `Cargo.toml`: `use pricing::discount_filter::DiscountFilter;` |
| Go | None. The test is in the package of the component |

### Rust and Go: the package

- **Rust.** A new file in `src` is a module only when `lib.rs` (or
  `main.rs`) declares it. The command does not edit another file. It writes
  the line to add on stderr: `add to src/lib.rs: pub mod discount_filter;`.
- **Go.** The package of the new files is the package of the other `.go`
  files in `<dir>`. With none, it is the name of the directory, in small
  letters, with each character that a Go name cannot have removed.

### What the command prints, and its exit code

On success, it prints each file that it made, one path in each line,
relative to the root, component first. Notes (the Rust line) go to stderr.

| Exit | Meaning | Files written |
|---|---|---|
| 0 | The files are made | Both |
| 1 | Refused: a file exists. The message names each such file, with the word `exists`: `discount_filter.py exists` | None |
| 2 | The command could not run: a bad kind, a bad name, a missing argument, a directory that cannot be made | None |

The command checks both files before it writes one: it writes both or
neither. The exit codes are those of the linters and of the compilers.

For a kind that is not made with `add`, the message says why, from the
table above. For `valve` it says: `A Valve is not a type. Make a Predicate
and a Filter, and join them with add_valve(predicate, filter).`

## Conformance

The cases are in [add/cases.json](add/cases.json). The same cases judge each
runtime: `python:add`, `typescript:add`, `rust:add`, `go:add`.

```json
{"id": "add/a-filter-gets-its-suffix",
 "args": ["filter", "Discount"],
 "expect": {"exit": 0,
            "type": "DiscountFilter",
            "files": {"python": ["discount_filter.py", "tests/test_discount_filter.py"],
                      "typescript": ["discount-filter.ts", "tests/discount-filter.test.ts"],
                      "rust": ["src/discount_filter.rs", "tests/discount_filter.rs"],
                      "go": ["discount_filter.go", "discount_filter_test.go"]}}}
```

| Key | Meaning |
|---|---|
| `args` | The arguments after `add` |
| `given` | Files that exist before the command runs, as `{language: {path: text}}`. Optional |
| `expect.exit` | The exit code |
| `expect.type` | The type name that the component file declares |
| `expect.files` | For each language, the files that the command prints, in order. Each one must exist after the run |
| `expect.contains` | A list of texts that the component file has, such as the description. Optional |
| `expect.message_contains` | Text that stderr has. Optional |

The judge is `python conformance/add.py` (or `python conformance/add.py
python:add`). It runs each case in a new, empty project of the language. Each
target is a file in [add/targets/](add/targets/), with these keys:

| Key | Meaning |
|---|---|
| `lang` | `python`, `typescript`, `rust` or `go`: the key of `expect.files` |
| `cmd` | The command; the `args` of the case come after it |
| `env` | The environment of the command |
| `setup` | `{path: text}`: the files of a new, empty project of the language, such as `Cargo.toml` and `src/lib.rs`, or `go.mod` |
| `lint` | A list of steps, each `{"cmd", "env", "quiet"}`. Each must exit 0; with `"quiet": true`, it must also print nothing (`gofmt -l`) |
| `test` | One step, `{"cmd", "env"}`: it runs the test file that the command made |

In a text of a target, `{repo}` is the root of this repository, `{project}`
the project of the case, `{python}` the Python that runs the judge,
`{pathsep}` the separator of a path list, and, in `lint` and `test`,
`{component}`, `{test}`, `{test_stem}` and `{component_dir}` the files that
the command printed. A target uses the packages of this repository, so the
judge checks the code of the branch, with no download.

For a case with exit 0, the judge also checks that:

1. **The linter finds nothing**, in strict mode, in the component file:
   `python -m codeupipe_lint.invariants --strict` and
   `python -m codeupipe_lint.anonymous_steps`, the TypeScript linter,
   `codeupipe-lint --strict` for Rust. Go has no linter yet; for Go the judge
   checks `gofmt -l` and `go vet`.
2. **The component builds**, or imports.
3. **The test fails with the known message.** One test runs, and it fails
   with `Write the acceptance case for <TypeName>.` Any other failure, such as
   a test that does not compile, fails the case. For Rust, the judge first
   adds the line that the command wrote on stderr.

For a case with an exit code other than 0, the judge checks that no file was
written, and that each file of `given` did not change.

The judge has tests of its own, with a fake command:
`tests/conformance/test_add_judge.py`.

| Target | Command | State |
|---|---|---|
| `python:add` | `python -m codeupipe_add`, in [packages/codeupipe-add/](../packages/codeupipe-add/) | Passes the 22 cases |
| `typescript:add` | `packages/codeupipe-add-ts` | Not yet |
| `rust:add` | `packages/codeupipe-add-rs` | Not yet |
| `go:add` | `packages/codeupipe-add-go` | Not yet |

## Phase 2: a layout

Phase 2 is not in the cases yet. This is the form that it will have.

```
codeupipe add --layout cup.layout.yaml
```

The layout file names the language, the directories, the components, and the
steps of each pipeline:

```yaml
lang: python            # python, typescript, rust or go
root: src/pricing       # the dir of the components
components:
  - kind: filter
    name: Discount
    description: Takes a rate off the price.
  - kind: predicate
    name: AtLeast
  - kind: filter
    name: MarkBulk
  - kind: tap
    name: Audit
  - kind: pipeline
    name: Pricing
    steps:
      - Discount
      - valve: [AtLeast, MarkBulk]
      - Audit
```

- Each component is made as in phase 1, with the same names, files and
  tests.
- **The steps of a pipeline** become its `add_filter`, `add_valve`,
  `add_tap` and `add_pipeline` calls, in order. A name in `steps` is a
  component of the file; its kind gives the call. `valve: [Predicate, Filter]`
  gives `add_valve`. A pipeline in `steps` is nested with `add_pipeline`.
- **A name in `steps` that is not a component of the file is refused** (exit
  2), as is a `valve` whose first name is not a Predicate or whose second
  name is not a Filter.
- **A file that exists is kept**, and the command says so. So a layout can
  grow: add a component to the file and run the command again. The pipeline
  file is not written again either; a change of steps in an existing
  pipeline is the user's work.

An ASCII tree (the output of `tree`) can come later as a second form of the
same layout. It has no place for the steps of a pipeline, so YAML is the
first form.

## Decisions

These are settled with the recommendation, as for the runtimes. A change
needs a change of this document and of the cases.

1. **A package of its own in each language**, as the linters and compilers
   are: `codeupipe-add` (Python), `codeupipe-add-ts`, `codeupipe-add-rs`,
   `codeupipe-add-go`. The runtime packages do not change, and a project that
   does not want the command does not get it.
2. **The templates are in each package**, in the form of its language. The
   cases, not shared template files, keep the four the same: a shared
   template would need a template language that each runtime reads.
3. **Phase 1 reads no YAML.** Phase 2 reads YAML. Python, Rust and Go have no
   YAML reader in their standard library, so the YAML reader is a declared
   dependency of the phase 2 command only. JSON is YAML, so a layout in JSON
   works too.

## Not in this contract yet

- A type of your own as a kind (`add data Order`).
- Acceptance cases as data in the layout, which would fill the test with a
  real case in place of the failing one.
- A check of the description against ASD-STE100.
