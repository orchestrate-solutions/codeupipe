# codeupipe for TypeScript

codeupipe is a library for writing a program as a pipeline of small steps.
This is the TypeScript runtime. It has no dependencies. The built JavaScript
runs in a browser and in Node.

It implements the same contract as the Python
package, and the same 27 conformance cases judge it:
[conformance/API.md](../../conformance/API.md).

```bash
npm install codeupipe
```

The version is below 1.0: the package is not stable yet, and a new version
can change in a way that is not compatible.

## The eight primitives

| Primitive | What it does | Who writes it |
|---|---|---|
| **Payload** | Carries the data | The library |
| **Filter** | Changes the data | You |
| **Predicate** | Asks a yes-or-no question about the data | You |
| **Valve** | Joins a Predicate to a Filter: the Filter runs when the answer is yes | The library. You add one with `addValve(predicate, filter)` |
| **Tap** | Reads the data as it goes by | You |
| **Hook** | Is called before and after each step | You |
| **State** | Records which steps ran | The library |
| **Pipeline** | Runs the steps in order | You |

## Example

[examples/pricing/](examples/pricing/) has one class in each file. The
pipeline file imports them and adds them.

```ts
// discount-filter.ts
import type { Filter, Payload } from "codeupipe";

export class DiscountFilter implements Filter {
  readonly rate: number;

  constructor(rate: number) {
    this.rate = rate;
  }

  call(payload: Payload): Payload {
    const price = payload.get("price", 0) * (1 - this.rate);
    return payload.insert("price", Math.round(price * 100) / 100);
  }
}
```

```ts
// at-least-predicate.ts
import type { Payload, Predicate } from "codeupipe";

export class AtLeastPredicate implements Predicate {
  readonly key: string;
  readonly minimum: number;

  constructor(key: string, minimum: number) {
    this.key = key;
    this.minimum = minimum;
  }

  test(payload: Payload): boolean {
    return payload.get(this.key, 0) >= this.minimum;
  }
}
```

```ts
// pricing-pipeline.ts
import { Pipeline } from "codeupipe";

import { AtLeastPredicate } from "./at-least-predicate.ts";
import { AuditTap } from "./audit-tap.ts";
import { DiscountFilter } from "./discount-filter.ts";
import { MarkBulkFilter } from "./mark-bulk-filter.ts";

export class PricingPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new DiscountFilter(0.1));
    // MarkBulkFilter runs only when the predicate is true.
    this.addValve(new AtLeastPredicate("qty", 10), new MarkBulkFilter());
    // A Tap failure is recorded and does not stop the run.
    this.addTap(new AuditTap());
  }
}
```

```ts
import { Payload } from "codeupipe";

const result = await new PricingPipeline().run(new Payload({ price: 100.0, qty: 12 }));
result.toDict();
// { price: 90, qty: 12, bulk: true }
```

In this repository the example imports from `../../src/index.ts`.

## Names

The names are the names of the contract, in camelCase.

| Contract | TypeScript |
|---|---|
| `add_filter`, `add_valve`, `add_tap`, `add_pipeline`, `use_hook` | `addFilter`, `addValve`, `addTap`, `addPipeline`, `useHook` |
| `run`, `state`, `labels`, `observe` | `run`, `state`, `labels`, `observe({ timing, lineage })` |
| `get`, `has`, `insert`, `remove`, `merge`, `copy` | the same |
| `to_dict`, `with_trace`, `trace_id`, `lineage` | `toDict`, `withTrace`, `traceId`, `lineage` |
| Hook: `before`, `after`, `on_error` | `before`, `after`, `onError` |

`Filter`, `Predicate` and `Tap` are interfaces: a class with the method is
one. `Hook` is a class with three methods that do nothing: extend it and
override the methods that you need.

## Differences from Python

- **There is one `run`, and it returns a Promise.** A Filter, a Tap or a
  Hook method can be sync or async. Python has `run` (sync) and `run_async`.
- **Absent is `null`.** `get` of a key that is not there gives `null`, and a
  Hook gets `null` as the step for the pipeline itself.
- **A function is not a step.** Every JavaScript function has a `call`
  method, so `addFilter` refuses a function by its type.
- **Two runs of one pipeline at the same time** each write to their own
  State. `pipeline.state` is the State of the run that started last.
- **The linter and the compiler are separate packages**, because they
  need a parser: [codeupipe-lint-ts](../codeupipe-lint-ts/) and
  [codeupipe-compile-ts](../codeupipe-compile-ts/). In Python the compiler is
  in the core package.

## Labels and minified code

State and Hooks report a step by its label, which is the name of its class.
A minifier changes class names, so a label in minified code can be a name
such as `b`. To keep the names, turn on the option of your tool that keeps
class names (for example `keepNames` in esbuild, `keep_classnames` in
terser). A class with no name has the label `anonymous`.

`tests/bundle.test.ts` checks this with esbuild: the pricing example gives
the same result in a plain bundle, a minified bundle and a minified bundle
that keeps names, and the labels change only in the second.
`examples/pricing/browser/entry.ts` is the entry of that bundle.

## Development

Node 22.18 or later runs the `.ts` files as they are.

The three TypeScript packages are one npm workspace. Run `npm ci` once, at
the root of the repository. Then, in this directory:

```bash
npm test             # the tests
npm run typecheck    # the type check of the source, tests and example
npm run build        # JavaScript and type files in dist/
node examples/pricing/main.ts
python ../../conformance/run.py typescript:run
```

The source uses only TypeScript syntax that can be removed without a
change to the code that runs: no `enum`, no parameter properties, no
`namespace`. One primitive is in each file, and the file name is the class
name in kebab-case.

## License

Apache License 2.0.
