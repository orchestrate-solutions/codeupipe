# codeupipe-lint for Rust

A linter for Rust code that uses codeupipe. It reads the source and does
not run it.

The linter is a codeupipe pipeline: [src/lint_pipeline.rs](src/lint_pipeline.rs).
Its steps carry a type of their own, `LintRun`, in place of a `Payload`,
because a run holds syntax trees. It depends on `codeupipe`, on `syn` to
parse the files, and on `serde_json` to read the config file.

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible. It is not on crates.io yet.
Build it from this repository:

```bash
cargo install --path packages/codeupipe-lint-rs
```

```bash
codeupipe-lint src                      # files or directories
codeupipe-lint --exclude '*/generated/*' src
codeupipe-lint --disable CUP-I005 src
codeupipe-lint --strict src             # a warning fails the run too
codeupipe-lint --rules                  # list the rule ids
codeupipe-lint                          # paths come from cup.config.json
```

Each finding is one line, and the message names the fix:

```
path:line:col  CUP-A005 unnamed-pipeline-step  Pipeline is a plain `Pipeline::new()`. A nested pipeline must be (...)
```

Exit code: **0** no findings, **1** findings, **2** a path could not be
read or the arguments cannot be used.

From Rust: `lint_paths(&paths, &LintOptions { exclude, disable, strict })`
returns the `LintRun` (`findings`, `suppressed`, `errors`, `report`,
`exit_code`).

## Rules

The ids are those of the Python and TypeScript linters.

| id | slug | what |
|---|---|---|
| CUP-I000 | parse-error | the file has a syntax error |
| CUP-A003 | local-type-step | a step whose type is declared in a function |
| CUP-A005 | unnamed-pipeline-step | a plain `Pipeline::new()` nested as a step |
| CUP-I003 | state-read-in-step | a Filter (`call`) or a Predicate (`test`) reads the State of a pipeline |
| CUP-I005 | one-primitive-per-file | a second primitive at the top level of a file |
| CUP-I006 | primitive-file-name | the file name is not the type name in snake_case |
| CUP-I007 | primitive-role-suffix | the type name does not end with its role |
| CUP-I008 | logic-outside-primitive | **a warning.** A function, an `impl` of a type that is not a primitive, a trait, or a `const` has logic (`if`, `match`, a loop, `let ... else`) |
| CUP-I009 | marker-allows-nothing | **a warning.** A `cup: allow-...` comment that allowed no finding |

A step is the argument of `add_filter`, `add_tap` or `add_pipeline` (on any
receiver), and the two arguments of `add_valve(predicate, filter)`.

A type is a primitive when it implements `Filter`, `Tap`, `Predicate`,
`Hook` or `NamedPipeline`, in the same file. Its role is the trait
(`NamedPipeline` is the role `Pipeline`).

## Rules that the compiler checks

The types of the Rust runtime refuse these, so the linter has no rule for
them:

| id | In Rust |
|---|---|
| CUP-A001, A002, A008 | A closure or a function is not a step and not a predicate: it does not implement the trait |
| CUP-A009 | An object literal does not exist in Rust |
| CUP-I004 | A Tap, a Predicate and a Hook get `&Payload`, so only a Filter can write |
| CUP-I001 | The data of a Payload is private |

A `--disable` or a `lint.disable` with one of these ids is an error, as for
any id the linter does not have.

## Logic that is not in a primitive (CUP-I008)

A project that uses codeupipe writes its logic as Filters, Predicates, Taps,
Hooks and Pipelines. Logic in a plain function or a plain type works as
well, so nothing else shows the mistake. This rule shows it.

- **It is a warning.** It is in the report and it is counted apart
  (`No findings. 3 warnings.`). It does not make the exit code 1. With
  `--strict`, a warning fails the run as a finding does.
- **Flagged:** a function, each `impl` of a type that is not a primitive
  (an inherent `impl` or a trait such as `Display`), a trait with a default
  method, and the first `const` or `static` whose value has logic. The
  modules of a file are checked the same way.
- **Not flagged:** the code of a primitive (each `impl` of a type that
  implements a primitive trait, so a helper method of a Filter is fine),
  code with no logic, code for the tests only (`#[test]`, `#[cfg(test)]`),
  and the files under `tests/`.
- **Not seen:** a loop that is a method call (`map`, `filter`, `for_each`),
  `&&`, `||`, `?`, and code in a macro call.
- For logic that must be plain code (the edge to a file or a server, the
  entry of a program), say why in a comment: `// cup: allow-plain <reason>`.

## Turn a finding off

- **One line.** A comment on the line of the finding, on the line of the
  `add_...` call around it, or alone on the line directly above:
  `// cup: allow-anonymous` for a CUP-A finding;
  `// cup: allow-state-read`, `allow-shared-file`, `allow-name` or
  `allow-plain` for a CUP-I finding. Any text can follow the marker.
  A finding of a function or a type is on the line of its name or of its
  `impl`, so the comment goes after the doc comment and the attributes:

  ```rust
  /// Reads the config file.
  #[inline]
  // cup: allow-plain the edge of the program: it reads a file before the pipeline runs
  pub fn read_config() -> Config {
  ```

  A comment that allows no finding is itself a finding (CUP-I009), so an
  old one does not stay. Text in a doc comment or a string is not a marker.
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

- A name is followed to the `let` that gave its value, in the same
  function, and a later `let` of the same name replaces it. A parameter, a
  pattern, a name from another file and the result of a call are not
  followed, so a function that returns a step of a local type is not seen.
- A type is matched by its name in the file. The linter reads syntax only:
  it does not resolve `use`, macros or types.
- The files under a `tests` directory are not checked by CUP-I005, I006,
  I007 and I008.

## Development

The linter is a Cargo workspace of its own, apart from the root workspace,
so that the runtime builds with no download. In this directory:

```bash
cargo test           # the tests, and the linter on the Rust code of this repository
cargo clippy --all-targets -- -D warnings
cargo run -q -- --strict src tests ../codeupipe-rs/src ../codeupipe-rs/examples ../codeupipe-rs/tests ../../conformance/runners/rust/src
```

## License

Apache License 2.0.
