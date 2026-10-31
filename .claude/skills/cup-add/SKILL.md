---
name: cup-add
description: >
  Make the files of codeupipe components with `codeupipe add` (also `cup add`):
  one component from the command line, or a whole project from a layout file
  (cup.layout.yaml) that lists the components and the steps of each pipeline.
  Each component file passes the linter, and each test starts at RED. Covers
  the command, the names it makes, the files for Python, TypeScript, Rust and
  Go, the layout keys, how steps become add_filter / add_valve / add_tap /
  add_pipeline / use_hook, what is refused, and the workflow from a scenario
  to a layout to GREEN. Use when starting a codeupipe project, adding a
  Filter, Predicate, Tap, Hook or Pipeline, writing or fixing a
  cup.layout.yaml, or when the user says "cup add", "codeupipe-add",
  "scaffold", or "layout".
---

# cup add

`codeupipe add` makes the files of codeupipe components. The contract is
[conformance/ADD.md](../../../conformance/ADD.md); this skill tells you how to
use it. If this skill and ADD.md do not agree, ADD.md is correct.

Two forms:

```
codeupipe add <kind> <name> [dir] [--description TEXT]   # one component
codeupipe add --layout cup.layout.yaml                    # each component of a layout
```

## What you get

For each component, two files:

- **The component.** One type, with its role suffix. It does nothing: a
  Filter returns the Payload with no change, a Predicate returns false, a Tap
  and a Hook do nothing, a Pipeline has no steps (or, from a layout, its
  steps). It passes the linter in strict mode.
- **The test.** One test, which fails on purpose with
  `Write the acceptance case for <TypeName>.` That is your RED. Replace the
  failure with a real case, see it fail for the right reason, then write the
  code.

The command never writes over a file.

## Run it in the root of the project

`dir` and the layout's `root` are relative to the directory where the
command runs. Run it in the root (where `pyproject.toml`, `package.json`,
`Cargo.toml` or `go.mod` is). Do not give an absolute path or a path with
`..`: the contract does not cover them yet, and the four languages do not do
the same thing with them.

| Language | The command | Install |
|---|---|---|
| Python | `codeupipe-add` or `python -m codeupipe_add` | `pip install codeupipe-add` (`codeupipe-add[layout]` for a YAML layout) |
| TypeScript | `node packages/codeupipe-add-ts/src/cli.ts` (in this repository) | the `codeupipe-add` workspace package (`npm ci` gets its `yaml` reader) |
| Rust | `cargo run --manifest-path packages/codeupipe-add-rs/Cargo.toml --` | build the `codeupipe-add` crate (its `layout` feature, on by default, reads YAML) |
| Go | build `packages/codeupipe-add-go/codeupipe-add`, then run the binary | `go build` (it gets gopkg.in/yaml.v3) |

In this repository, the packages are not on a registry yet; run them from
their directories.

## The kinds

| Kind | Suffix | Notes |
|---|---|---|
| `filter` | `Filter` | Writes to the Payload |
| `predicate` | `Predicate` | A yes-or-no question. Not a step: it goes in a valve. Name it for the case where the filter runs |
| `tap` | `Tap` | Reads only |
| `hook` | `Hook` | Called before and after each step, and on an error. Not a step: it goes in `hooks` |
| `pipeline` | `Pipeline` | Joins the others |

A Valve is not a kind: it is `add_valve(predicate, filter)`. Make the
Predicate and the Filter. Payload and State are made by the runtime.

## Names

- `Discount`, `discount`, `at_least` and `at-least` are all good. Each `_`
  and `-` starts a word: `at_least` gives `AtLeast`.
- The suffix is added when the name does not end with it:
  `filter Discount` gives `DiscountFilter`; `filter DiscountFilter` gives
  the same. So a pipeline named `Checkout` is `CheckoutPipeline`; you cannot
  get a type named only `Checkout`.
- The file name is the type name broken into words, in small letters:
  `HTTPGetFilter` gives `http_get_filter` (`http-get-filter` in TypeScript).
- A name starts with a letter and has only letters, digits, `_` and `-`.

## The files of each language

`filter Discount src/pricing` gives:

| Language | Component | Test |
|---|---|---|
| Python | `src/pricing/discount_filter.py` | `tests/test_discount_filter.py` |
| TypeScript | `src/pricing/discount-filter.ts` | `tests/discount-filter.test.ts` |
| Rust | `src/pricing/discount_filter.rs` | `tests/discount_filter.rs` |
| Go | `src/pricing/discount_filter.go` | `src/pricing/discount_filter_test.go` |

Things to do after the command:

- **Python.** The test imports `from src.pricing.discount_filter import
  DiscountFilter`, so the root must be on the import path: run
  `PYTHONPATH=. python -m pytest`. The command makes no `__init__.py`. To
  record this in the project, so that `python -m pytest` works with no
  variable, put it in `pyproject.toml` (pytest 7 or later):

  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]
  ```
- **Rust.** A new file is a module only when a parent declares it. The
  command prints the lines to add on stderr, such as
  `add to src/lib.rs: pub mod pricing;` and
  `add to src/pricing.rs: pub mod discount_filter;`. Add each one. With a
  layout, the lines of all the components come together, each line once.
- **Go.** The package is that of the other `.go` files in the directory, or
  the directory name.

## Exit codes

| Exit | Meaning | Files written |
|---|---|---|
| 0 | Made (with `--layout`, also when some files were kept) | All the new ones |
| 1 | One component: a file exists. The message names it with `exists` | None |
| 2 | The arguments or the layout cannot be used. The message says why | None |

Options are written in full: `--desc` is refused. Use `--description`.

## The layout

A layout is the plan of a project in one file. It stays in the project as a
record of its structure. Write it first, then run the command.

```yaml
lang: python            # the language of the command: python, typescript, rust or go
root: checkout          # the directory of the component files (default: .)
components:
  - kind: filter
    name: ValidateOrder
    description: "Puts the subtotal of the items in the Payload."
  - kind: predicate
    name: IsMember
    description: "True when the customer is a member."
  - kind: filter
    name: MemberDiscount
    description: "Takes ten percent off the subtotal."
  - kind: filter
    name: AddTax
  - kind: tap
    name: AuditLog
  - kind: hook
    name: Timing
  - kind: pipeline
    name: Checkout
    description: "Prices an order."
    steps:
      - ValidateOrder
      - valve: [IsMember, MemberDiscount]
      - AddTax
      - AuditLog
    hooks:
      - Timing
```

```bash
codeupipe-add --layout cup.layout.yaml
```

The keys:

| Key | Where | Meaning |
|---|---|---|
| `lang` | top, required | Must be the language of the command |
| `root` | top | The directory of the component files. Use a package name (`checkout`, `src/pricing`), so that the imports say where a component is: `from checkout.add_tax_filter import AddTaxFilter`. With `.`, the files go beside `cup.layout.yaml` |
| `components` | top, required | One or more, made in this order |
| `kind`, `name` | each, required | As on the command line |
| `description` | each | The header comment of the component file (in Python, the module docstring: `"""AddTaxFilter: <description>"""`). Write it: it is the first thing a reader sees |
| `steps` | pipeline only | In order. A name, or `valve: [Predicate, Filter]` |
| `hooks` | pipeline only | Names of hooks |

Any other key is refused, so a typing error (`step:`) is found at once. A
key that is two times in one mapping (two `description:` lines in one
component) is refused too.

**Put each `description` in quotes.** In YAML, `: ` in a text that is not in
quotes starts a mapping: `description: Prices an order: validate, tax` is
refused by the YAML reader. `description: "Prices an order: validate, tax"`
is correct.

How steps become code (Python; the other languages make the same calls in
their own form):

| In the layout | In the pipeline |
|---|---|
| a filter name | `self.add_filter(DiscountFilter())` |
| a tap name | `self.add_tap(AuditLogTap())` |
| a pipeline name | `self.add_pipeline(TaxPipeline())` (nested) |
| `valve: [IsMember, MemberDiscount]` | `self.add_valve(IsMemberPredicate(), MemberDiscountFilter())` |
| a name in `hooks` | `self.use_hook(TimingHook())` |

| Language | A valve in the pipeline file | Imports of the steps |
|---|---|---|
| TypeScript | `this.addValve(new IsMemberPredicate(), new MemberDiscountFilter());` in the constructor | `import { IsMemberPredicate } from "./is-member-predicate.ts";` |
| Rust | `pipeline.add_valve(IsMemberPredicate, MemberDiscountFilter);` in `add_steps`; a nested pipeline is `Pipeline::named(TaxPipeline)` | `use crate::checkout::is_member_predicate::IsMemberPredicate;` (the `root` must be under `src`; the default is `src`) |
| Go | `pipeline.AddValve(IsMemberPredicate{}, MemberDiscountFilter{})` in `AddSteps`; a nested pipeline is `codeupipe.NewNamedPipeline(TaxPipeline{})` | None: the components of a layout are in one package |

- **A valve runs its filter only when the predicate is true.** When it is
  false, the filter is skipped and the run goes on. So name the predicate for
  the case where the filter must run: `valve: [NeedsTranslation,
  TranslateText]`, not `valve: [IsEnglish, TranslateText]` (that translates
  the English texts).
- **A valve guards one filter.** To guard two or more, give each its own
  valve with the same predicate:

  ```yaml
  steps:
    - valve: [HasError, BuildAlert]
    - valve: [HasError, PutInOutbox]
  ```

  The predicate is asked again before each filter, so keep it a question
  about the Payload, with no slow work in it. A pipeline cannot go in a
  valve.
- **"This, else that" is two valves with opposite predicates**, one for each
  path:

  ```yaml
  steps:
    - valve: [NotShipped, PayRefund]
    - valve: [Shipped, MakeReturnLabel]
    - AddHistoryNote        # both paths
  ```

  The second predicate is asked after the first filter ran. If that filter
  can change what the second predicate reads, both paths can run: test the
  pipeline with both cases.
- **A name with `Not` is correct when that is the case where the filter
  runs.** The rule is "true when the filter must run", not "no negative
  names": `NotShipped` before `PayRefund` is right; `Shipped` before
  `PayRefund` is wrong.
- A step names a component **of the same file**, by its `name` or its type
  name (`Discount` or `DiscountFilter`).
- Each step is made with **no arguments**. If a component needs a setting
  (a rate, a key), give it a default in its `__init__` when you write it.
- One component can be a step of more than one pipeline. A pipeline can be
  a step of another, but not of itself, directly or through another.

Refused, with exit 2 and nothing written: no `lang`, another `lang`, an
unknown key, an empty `components`, a bad kind or name, two components with
the same type name, `steps` or `hooks` on a component that is not a
pipeline, a step that is not in the file, a predicate or a hook as a step, a
valve that is not `[Predicate, Filter]`, a pipeline that contains itself,
and `--layout` with a kind, a name, a dir or `--description`.

### Grow a layout

Run the command again after you add a component to the file. It writes the
new files, and keeps each file that exists:
`checkout/add_tax_filter.py exists, kept` (on stderr). It does not write a
pipeline file again, so **when you change the steps of a pipeline that
exists, change its file yourself**, and keep the layout the same as the
code.

The command tells you which pipeline files to change. When the steps of a
kept pipeline file are not the steps of the layout, it says so on stderr:

```
checkout/checkout_pipeline.py exists, kept, and its steps are not those of the layout. Change the file: the command does not write it again.
```

Change the file, then run the command again: the line goes away when the
steps are the same. The arguments of a step and the comments do not count,
so `DiscountFilter(0.1)` is the same step as `DiscountFilter()`.

## Workflow: from a scenario to GREEN

1. **Read the scenario and find the steps.** Each thing that changes the data
   is a Filter. Each yes-or-no question is a Predicate, and the Filter that it
   guards goes in a valve with it; the question is true when the Filter must
   run ("only when there is an error" gives `HasError`). Each thing that only reads (a log, a
   metric) is a Tap. Each thing that watches every step (timing, tracing) is
   a Hook. A group of steps that is used in more than one place, or that has
   a name of its own, is a nested Pipeline.
2. **Write `cup.layout.yaml`** with a `description` for each component, in
   quotes.
3. **Run `codeupipe-add --layout cup.layout.yaml`.** Read what it printed.
4. **Lint:** `python -m codeupipe_lint.invariants --strict <root>` finds
   nothing.
5. **Run the tests:** `PYTHONPATH=. python -m pytest -q`. Each test fails with
   `Write the acceptance case for ...`. That is the RED of each component.
6. **One component at a time:** write its acceptance case, see it fail for the
   right reason, write the code, see it pass. Do the Filters and Predicates
   first, then the pipeline.
7. **Lint again.** Commit.

## Mistakes to look for

| Mistake | What happens | Do this |
|---|---|---|
| A predicate as a step | Refused: "put it in a valve" | `valve: [IsMember, MemberDiscount]` |
| A predicate named for the other case (`IsEnglish` before `TranslateText`) | Not refused: the filter runs on the wrong texts | Name it for when the filter runs: `NeedsTranslation` |
| Two filters in one valve (`valve: [HasError, BuildAlert, PutInOutbox]`) | Refused: a valve is [Predicate, Filter] | One valve for each filter, the same predicate |
| `description: Prices an order: validate` | Refused by the YAML reader | Put the description in quotes |
| The same key two times in one component | Refused, with the line | Keep one |
| A hook as a step | Refused: "put it in hooks" | `hooks: [Timing]` |
| `valve: [MemberDiscount, IsMember]` | Refused: the order is [Predicate, Filter] | Predicate first |
| A step that is not a component of the file | Refused, with its name | Add the component, or fix the name |
| `name: CheckoutPipeline` and `name: Checkout` for two pipelines | Refused: same type name | One name for each component |
| A component with a setting, made with no arguments | The step is made with no arguments | A default in `__init__` |
| Steps changed in the layout after the first run | The pipeline file is kept, and stderr says its steps are not those of the layout | Change the pipeline file yourself |
| `--desc` | Refused | `--description` |
| Run from a subdirectory | Files in the wrong place | Run in the root of the project |
| Python tests cannot import the component | `ModuleNotFoundError` | `PYTHONPATH=.` |

## Not yet

- Acceptance cases as data in the layout.
- A type of your own (`add data Order`).
- A rule for an absolute `dir` or a `dir` with `..`.
