# codeupipe-add for TypeScript

`codeupipe add` for TypeScript: it makes the files of one component. The
contract is [conformance/ADD.md](../../conformance/ADD.md), and this command
passes all its cases (`python conformance/add.py typescript:add`).

```bash
node src/cli.ts filter Discount src/pricing --description "Takes a rate off the price."
```

```
src/pricing/discount-filter.ts
tests/discount-filter.test.ts
```

- **The kinds** are `filter`, `predicate`, `tap`, `hook` and `pipeline`.
- **The role is added** when the name does not end with it: `filter Discount`
  gives `DiscountFilter`. `at_least` and `audit-log` give `AtLeast...` and
  `AuditLog...`.
- **The file name** is the type name in kebab-case, the rule of the linters
  (CUP-I006): `HTTPGetFilter` goes in `http-get-filter.ts`.
- **The component does nothing**, and passes the linter in strict mode.
- **The test fails on purpose**, with `Write the acceptance case for
  DiscountFilter.` Start there.
- **A file is never written over.** If one of the two exists, nothing is
  written, and the exit code is 1.

Run it in the root of the project. The test is in `tests/` and imports the
component by its path from there (`import { DiscountFilter } from
"../src/pricing/discount-filter.ts"`), so the test runs with `node --test
tests/discount-filter.test.ts`.

Exit code: **0** the files are made, **1** a file exists, **2** the
arguments cannot be used. Nothing is written on 1 or 2.

## A layout

`node src/cli.ts --layout cup.layout.yaml` makes the files of each component
in the file, and the steps of each pipeline (ADD.md, "Phase 2: a layout"):

```yaml
lang: typescript
root: src/pricing
components:
  - {kind: filter, name: Discount, description: "Takes a rate off the price."}
  - {kind: predicate, name: AtLeast}
  - {kind: filter, name: MarkBulk}
  - kind: pipeline
    name: Pricing
    steps: [Discount, {valve: [AtLeast, MarkBulk]}]
```

The pipeline file imports each step from beside it (`./discount-filter.ts`)
and calls `this.addValve(new AtLeastPredicate(), new MarkBulkFilter())` in
its constructor. The `yaml` package reads the file (YAML or JSON); only
`--layout` loads it. A file that exists is kept, so a layout can grow: add a
component and run the command again.

The version is below 1.0: the package is not stable yet. It is not on npm.

## Development

The command is a codeupipe pipeline of five Filters,
[src/add-pipeline.ts](src/add-pipeline.ts), and one of seven for a layout,
[src/layout-pipeline.ts](src/layout-pipeline.ts). Its tests are in `tests/`, and
the conformance cases in `conformance/add/`.

```bash
npm test             # builds the core package first, then runs the tests
npm run typecheck
npm run build        # JavaScript and type files in dist/
```

## License

Apache License 2.0.