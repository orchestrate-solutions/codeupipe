# codeupipe-compile for TypeScript

Writes a codeupipe pipeline as one plain TypeScript module with no import
of codeupipe. It reads the source and does not run it. It is a beta.

**The rule: code that compiles gives the same output as the pipeline. A
pipeline for which the compiler cannot keep that rule is refused, with the
place named.** A pipeline that compiles and then behaves in a different way
is a bug.

The compiler is a codeupipe pipeline:
[src/compile-pipeline.ts](src/compile-pipeline.ts). It depends on
`codeupipe` and on the `typescript` package, which it uses to read and
write code.

```bash
npm install --save-dev codeupipe-compile@beta
npx codeupipe-compile src/pricing-pipeline.ts:PricingPipeline --out build/pricing.ts
```

Exit code: **0** the module is written, **1** the pipeline is refused (the
message names the place and the fix), **2** the command could not run.
Nothing is written on 1 or 2.

From TypeScript: `await compile(file, className, { outFile })` returns the
text of the module, and throws `CompileRefusal`.

## Example

The pricing example of the core package compiles to this module:

```ts
const cup_01_discount_filter_rate: number = 0.1;
function cup_01_discount_filter(payload: Map<string, unknown>) {
    const price = cup_get(payload, "price", 0) * (1 - cup_01_discount_filter_rate);
    return payload.set("price", Math.round(price * 100) / 100);
}

// ... one function for each step ...

export async function run(input: Record<string, unknown>): Promise<Record<string, unknown>> {
  const data = new Map<string, unknown>(Object.entries(input));
  cup_01_discount_filter(data);
  if (cup_02_when_at_least_predicate(data)) cup_02_mark_bulk_filter(data);
  try { cup_03_audit_tap(data); } catch { /* a Tap failure does not stop the run */ }
  return Object.fromEntries(data);
}
```

`run` takes a plain object and returns a new plain object. The object that
the caller gives is not changed.

## What compiles

| Shape | Plain form |
|---|---|
| A pipeline class | `export async function run(input)`. The class extends `Pipeline`, and its constructor calls `super()` and then only adds steps |
| Filter (`call`) | A function on a `Map`. An `async call` is awaited |
| Valve | `if (predicate(data)) filter(data);` |
| Tap (`observe`) | The call in `try`/`catch`: a failure does not stop the run |
| Nested pipeline | Its steps, in place |
| A setting of an instance (`this.rate`) | A constant, from the literal that `new DiscountFilter(0.1)` gives |
| `get`, `has`, `insert`, `remove`, `toDict`, `merge(new Payload(map))` | Operations on the `Map` |
| An import of a step file | The same import, relative to the compiled file |

A step is made in the call that adds it: `this.addFilter(new X(...))`. The
arguments are literals: text, numbers, `true`, `false`, `null`, and lists
and objects of them.

## What is refused

| Shape | What to do |
|---|---|
| A Hook, or `observe(...)` on the pipeline | The compiled code has no lifecycle and no State. Run the pipeline itself |
| A constructor of the pipeline that does more than add steps | Keep only `super()` and the `add...` calls |
| An argument that is not a literal, or a setting that the constructor computes | Give literal settings, and compute in the method |
| A step that assigns to `this`, calls its own helper method, or extends a class | Put the code of the step in one method of one class |
| A Filter that returns something that is not the Payload it was given | Return the payload, or a write on it |
| `copy`, `withTrace`, `traceId`, `lineage` | Plain data has none of these. Run the pipeline itself |
| The Payload under another name, or given to other code | Use it only through its operations |
| A Tap or a Predicate that writes, an async Predicate | Only a Filter writes |
| A name that the step file declares beside the class | Move it to its own file and import it |
| A step class from a package | Compile steps whose source is in the project |

The tests for each refusal are in [tests/refusals.test.ts](tests/refusals.test.ts).

## What the compiled code does not have

- **State.** No `executed`, `skipped`, `errors` or `timings`.
- **Hooks.** A pipeline with a Hook is refused.
- **Tap errors.** They are contained, as in the pipeline, but they are not
  recorded.
- **Labels.** A function has a name such as `cup_01_discount_filter`.

So the conformance suite judges the target `typescript:static` on output,
on Taps and on an unchanged input: 11 cases pass, and the 16 cases that
also check State or Hooks pass on what the code can show.

The compiled module is like one instance of the pipeline: a setting that is
a list or an object is one value for every run.

## Differences from the Python compiler

Python has `python -m codeupipe.compile`. It reads a pipeline object that is
in memory. This compiler reads the source of a pipeline class. Python also
has an inline layout and an observable mode (State and Hooks); this
compiler has neither.

## Development

The three TypeScript packages are one npm workspace. Run `npm ci` once, at
the root of the repository. Then, in this directory:

```bash
npm test             # builds the core package first, then runs the tests
npm run typecheck    # also checks the conformance runner
npm run build        # JavaScript and type files in dist/
python ../../conformance/run.py typescript:static
```

## License

Apache License 2.0.
