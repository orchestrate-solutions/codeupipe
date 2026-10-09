# @codeupipe/core — TypeScript

TypeScript runtime of the codeupipe core pipeline primitives. Zero dependencies.

All runtimes share the same 8 primitives. Each is a first-class citizen optimized for its domain: **TypeScript** for web + browser, **Python** for prototypes + backend, **Rust** for WASM + desktop, **Go** for cloud, **C#** for .NET + games.

## Quick Start

```typescript
import { Payload, Pipeline, type Filter } from "@codeupipe/core";

export class Greet implements Filter {
  call(payload: Payload) {
    const name = payload.get("name") as string;
    return payload.insert("greeting", `Hello, ${name}!`);
  }
}

const pipeline = new Pipeline().addFilter(new Greet());

const result = pipeline.run(new Payload({ name: "World" }));
console.log(result.get("greeting")); // "Hello, World!"
pipeline.state.executed; // ["my-app/src/greet#Greet"]
```

## Step identity: the required build step

Steps have no names. Each is identified by the declaration of its filter,
`<package>/<source path>#<Name>` (`#2` from the second use), which State,
Hooks and the event log report (conformance/API.md, "Step identity").

JavaScript cannot know at runtime which module a class came from, and
minifiers rename classes, so **a build step stamps every top-level class and
function declaration** with its identity, as a string literal that survives
minification. The runtime reads the stamp and **refuses a step without one**:
object literals, arrow functions, closures, classes declared inside a
function, and a plain `new Pipeline()` nested as a step (nest a named
subclass: `class Onboarding extends Pipeline {}`). Valve predicates are
objects: a top-level class implementing `Predicate` (`test(payload)`), with
any configuration on the instance (`new Valve(f, new AtLeast(5))`).

Pick the adapter for your toolchain (all share `identity/stamp.ts`):

| Toolchain | Adapter |
|---|---|
| vitest / Vite | `plugins: [cupIdentity()]` from `identity/vite_plugin.ts` (see `vitest.config.ts`) |
| Bun | `bun run --preload ./identity/bun_preload.ts app.ts`, or `preload` in `bunfig.toml` |
| tsc | `tsc && bun run identity/stamp_dist.ts dist` (labels come from the source maps, so compiled code reports the same identities as the source) |

Verified: identities are identical from source (vitest, Bun) and from tsc
output run by plain Node, and survive a minified bundle
(`tests/step_identity.test.ts`).

## Core Types

| Type | Role |
|------|------|
| `Payload<T>` | Immutable data container |
| `MutablePayload<T>` | Mutable sibling for bulk edits |
| `Filter<TIn, TOut>` | Processing unit — `call(payload) → Promise<Payload>` |
| `StreamFilter<TIn, TOut>` | Streaming — `stream(chunk)` yields 0..N |
| `Pipeline<TIn, TOut>` | Orchestrator — `.run()` / `.stream()` |
| `Valve<TIn, TOut>` | Conditional gate — filter + predicate |
| `Tap<T>` | Read-only observer — `.observe(payload)` |
| `State` | Execution metadata |
| `Hook<T>` | Lifecycle — before / after / onError |

## Tests

```bash
npm test          # vitest run
npm run test:watch # vitest watch mode
```
