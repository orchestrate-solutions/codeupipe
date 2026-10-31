# codeupipe-add for Rust

`codeupipe add` makes the files of a component: the component file and one
test that fails, so that the work starts at RED. The contract is
[conformance/ADD.md](../../conformance/ADD.md), and the same 47 cases judge
each language (`python conformance/add.py rust:add`).

The command is a codeupipe pipeline:
[src/add_pipeline.rs](src/add_pipeline.rs), and
[src/layout_pipeline.rs](src/layout_pipeline.rs) for a layout. Its steps
carry types of their own, `AddRun` and `LayoutRun`, in place of a `Payload`,
because a run holds paths and text rather than JSON-shaped values. It
depends on `codeupipe`, and, for `--layout`, on `yaml-rust2` (the `layout`
feature, on by default). With `--no-default-features` it has nothing to
download.

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible. It is not on crates.io yet.
Build it from this repository:

```bash
cargo install --path packages/codeupipe-add-rs
```

```bash
codeupipe add filter Discount                       # src/discount_filter.rs and tests/discount_filter.rs
codeupipe add predicate at_least src/pricing        # src/pricing/at_least_predicate.rs
codeupipe add tap Audit --description "Writes a line for each run."
```

The component does nothing, and the test fails with
`Write the acceptance case for AuditTap.`: the contract asks for a beginning,
not for work already done. A file that exists is never written over, and the
command writes both files or neither.

Rust needs one thing more, because a new file in `src` is a module only when
the crate says so. The command edits no file that is there already, so it
writes each line that the crate needs on stderr, and you add them:

```
add to src/lib.rs: pub mod discount_filter;
```

A component in a directory of its own needs two, since the crate names the
directory and the directory names the component:

```
codeupipe add filter Discount src/pricing
add to src/lib.rs: pub mod pricing;
add to src/pricing.rs: pub mod discount_filter;
```

Exit code: 0 the files are made, 1 a file exists (nothing is written), 2 the
arguments cannot be used (nothing is written). The same codes as the linters
and the compilers.

## The steps

| Step | What it does |
|---|---|
| `TypeNameFilter` | kind and name to `DiscountFilter` and `discount_filter` |
| `PlanFilesFilter` | the two paths, relative to the root of the project |
| `CrateNameFilter` | the name of the crate, which the test imports |
| `RefuseExistingFilter` | a file that exists stops the run, and names it |
| `RenderFilesFilter` | the text of the two files, from the templates |
| `DirectoryModuleFilter` | the file of a component directory of its own |
| `ModuleLineFilter` | the lines that the crate needs, for stderr |
| `WriteFilesFilter` | the two files, and the directories that they need |

## Tests

```bash
cargo test          # the steps, and the whole pipeline on a project of its own
cargo fmt
cargo clippy -- --strict
```

## A layout

`codeupipe add --layout cup.layout.yaml` makes the files of each component
in the file, and the steps of each pipeline (ADD.md, "Phase 2: a layout"):

```yaml
lang: rust
root: src/pricing
components:
  - {kind: filter, name: Discount, description: "Takes a rate off the price."}
  - {kind: predicate, name: AtLeast}
  - {kind: filter, name: MarkBulk}
  - kind: pipeline
    name: Pricing
    steps: [Discount, {valve: [AtLeast, MarkBulk]}]
```

The pipeline file has `use crate::pricing::discount_filter::DiscountFilter;`
for each step, and `pipeline.add_valve(AtLeastPredicate, MarkBulkFilter);`.
The lines for the crate come on stderr, each once. A file that exists is
kept, so a layout can grow: add a component and run the command again.
