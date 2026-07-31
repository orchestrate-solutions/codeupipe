
<!-- agent-file-index:begin -->
## 📁 File Index — fetch only what you need

> **Stable v1 URLs** — everything under `/cup/v1/` is a versioned surface. Older URLs may keep working, but agents should prefer `/v1/agents.md` (agents.md convention).

This brief is the entrypoint. Every primitive lives in its own file so agents can
pull just the spec they need instead of loading the whole context.

| Primitive | Spec | Runtime source (TS) |
|---|---|---|
| **system_overview** | [`docs/system-overview.md`](/cup/v1/docs/system-overview.md) — T0 — the whole picture. Read this first if you don't know CUP. | [`runtime/index.js`](/cup/v1/runtime/index.js) |
| **payload** | [`docs/payload.md`](/cup/v1/docs/payload.md) — T0 — the immutable data envelope. | [`runtime/payload.js`](/cup/v1/runtime/payload.js) |
| **filter** | [`docs/filter.md`](/cup/v1/docs/filter.md) — T0 — the atomic unit of work (one Payload in, one Payload out). | [`runtime/filter.js`](/cup/v1/runtime/filter.js) |
| **pipeline** | [`docs/pipeline.md`](/cup/v1/docs/pipeline.md) — T0 — the ordered composition of Filters. | [`runtime/pipeline.js`](/cup/v1/runtime/pipeline.js) |
| **valve** | [`docs/valve.md`](/cup/v1/docs/valve.md) — T0 — pure predicate gating a Filter. | [`runtime/valve.js`](/cup/v1/runtime/valve.js) |
| **tap** | [`docs/tap.md`](/cup/v1/docs/tap.md) — T0 — read-only observer, async handoff for side-effects. | [`runtime/tap.js`](/cup/v1/runtime/tap.js) |
| **hook** | [`docs/hook.md`](/cup/v1/docs/hook.md) — T0 — before/after/on_error lifecycle callback. | [`runtime/hook.js`](/cup/v1/runtime/hook.js) |
| **state** | [`docs/state.md`](/cup/v1/docs/state.md) — T0 — execution metadata ledger (never seen by Filters). | [`runtime/state.js`](/cup/v1/runtime/state.js) |

Machine-readable manifest: [`agent-context.json`](/cup/v1/context.json).
Playground templates: [`playground-templates.js`](/cup/v1/playground-templates.js).

**Recommended fetch order for a cold agent:**
1. This file (`agent.md`) — mental model & contracts.
2. `agent-context.json` — machine index of everything else.
3. Individual `docs/*.md` files on demand.

<!-- agent-file-index:end -->

# codeupipe — Agent Brief

> **You are working with Codeupipe (CUP).** Everything you need to design, review,
> and build with CUP lives in this file. It is deliberately language-agnostic.
> All runtimes share the same seven primitives; only the surface syntax changes.

---

## 1. The One-Sentence Model

> **A `Payload` (immutable data) flows through a `Pipeline` (ordered blueprint) of `Filter`s (atomic units of work), gated by `Valve`s (pure predicates), observed by `Tap`s (read-only) and `Hook`s (lifecycle), while `State` tracks execution metadata off to the side.**

If you remember nothing else, remember that sentence.

---

## 2. The Four Values (Manifesto)

We value each on the left more than each on the right:

| Prefer | Over |
|---|---|
| **I. Immutable Data Flow** | in-place mutation |
| **II. Declarative Pipeline Composition** | procedural routing logic |
| **III. Detached Concurrency** | blocking synchronous side-effects |
| **IV. Statically Inspectable Blueprints** | opaque runtime black boxes |

CUP is a **paradigm**, not a specific framework. It applies to backend services,
frontend UI, mobile apps, data pipelines, and embedded systems alike.

---

## 3. The Two Planes

Every CUP system separates work across two execution planes.

### Plane A — Synchronous Conveyor (core transaction)

Everything the transaction cannot succeed without.

- **Payload** — the immutable data envelope
- **Filter** — one Payload in, one Payload out
- **Pipeline** — the ordered composition
- **Valve** — the conditional gate

### Plane B — Detached Boundary (observation & side-effects)

Everything the transaction should not wait for.

- **Tap** — read-only observer; async handoff for I/O
- **Hook** — before / after / on_error lifecycle callback
- **State** — execution metadata ledger

**Rule:** if this action fails, must the whole operation fail?
Yes → **Filter**. No → **Tap**.

---

## 4. The Seven Primitives — Complete Contracts

### 4.1 Payload
- **Shape:** keyed container, `string → any`.
- **API:** `get(key)` → value or null-equivalent (never raises). `insert(key, value)` → **new** Payload.
- **Invariants:**
  - Never mutated in place.
  - `insert` never modifies the receiver.
  - Missing keys never raise.
- **Anti-pattern:** `payload._data["k"] = v` — reaches past the contract.

### 4.2 Filter
- **Signature:** `call(payload) → payload`.
- **Rules:**
  - Pure-ish. Same input → same output.
  - Never mutates the input Payload.
  - One class per file. PascalCase class, snake_case filename.
  - Configuration goes on the instance (constructor). Per-invocation data goes on the Payload.
- **Invariants:**
  - Always returns a Payload — never `null`, never omits.
  - Never contains `if/else` branching that changes the pipeline path (that's a Valve).
  - Never reads or writes State.
- **Anti-pattern:** branching or routing logic inside a Filter.

### 4.3 Pipeline
- **Shape:** ordered list of steps. Each step is a Filter or another Pipeline.
- **API:** `run(payload) → payload`.
- **Rules:**
  - Nesting is legal — a Pipeline **is** a step.
  - Error in step N halts by default; a Hook may intercept.
- **Invariants:**
  - Steps execute in declared order.
  - Each step receives the previous step's output, not the original input.
- **Anti-pattern:** manually calling filters in a function instead of declaring a Pipeline.

### 4.4 Valve
- **Shape:** wraps exactly one Filter (or nested Pipeline).
- **Predicate:** pure function `payload → boolean`.
- **Behavior:** true → run the wrapped step. False → pass-through unchanged.
- **Invariants:**
  - Predicate is pure — no mutation, no external calls.
  - False never modifies the Payload.
  - The Valve is declared in the Pipeline, not hidden inside a Filter.
- **Anti-pattern:** predicate with side effects; branching inside a Filter.

### 4.5 Tap
- **Signature:** `on_payload(payload) → void`.
- **Rules:**
  - Cannot modify the Payload.
  - Failure inside a Tap does not halt the Pipeline.
  - Heavy I/O must be dispatched to the async detached boundary — never block the belt.
- **Invariants:**
  - Removing every Tap yields the identical Pipeline output.
- **Anti-pattern:** synchronous HTTP inside a Tap; Tap that mutates Payload.

### 4.6 Hook
- **Callbacks:** `before(name, payload)`, `after(name, payload)`, `on_error(name, payload, error)`.
- **Return values:** `before` / `after` are void. `on_error` may return `retry | skip | propagate`.
- **Rules:**
  - Multiple Hooks compose; they fire in registration order.
  - Hook cannot change the Payload the Filter receives (that's a Filter's job).
- **Invariants:**
  - A Hook that raises is a bug in the Hook.
- **Anti-pattern:** business logic in a Hook.

### 4.7 State
- **Shape:** structured execution metadata — step count, timings, errors, retries, current step.
- **Scope:** per Pipeline run.
- **Visibility:** available to Hooks and Taps. **Not visible to Filters.**
- **Invariants:**
  - Filters do not read or write State.
  - State never carries domain data.
- **Anti-pattern:** storing `_step_count` or `_started_at` on the Payload.

---

## 5. Decision Framework

Use this ladder when designing anything in CUP:

1. **Does this transform data?** → Filter.
2. **Should this only run under a condition?** → Wrap the Filter in a Valve.
3. **Is this observation only (logs, metrics, events)?** → Tap.
4. **Is this lifecycle (retry, timing, tracing)?** → Hook.
5. **Is this "how the pipeline is running"?** → State.
6. **Is this "what the pipeline is working on"?** → Payload.
7. **If this action fails, must the whole operation fail?** Yes → Filter. No → Tap.
8. **Do I need branching?** Elevate it to a Valve on the Pipeline. Do not hide it in a Filter.

---

## 6. Runtimes

CUP has six official runtimes in this repository. Same primitives, same contracts;
idiomatic surface syntax per language.

| Runtime | Path | Package | Use Cases |
|---|---|---|---|
| Python | [`codeupipe/`](../codeupipe) | `pip install codeupipe` | canonical reference, data, ML, backend |
| TypeScript | [`runtimes/ts/`](../runtimes/ts) | `@codeupipe/core` | web, browser, node, edge |
| Rust | [`runtimes/rs/`](../runtimes/rs) | `codeupipe` (crate) | WASM, desktop, embedded, perf-critical |
| Go | [`runtimes/go/`](../runtimes/go) | `codeupipe` module | cloud services, concurrent servers |
| C# | [`runtimes/cs/`](../runtimes/cs) | `CupPipe` | .NET, Unity, sync-first |
| Kotlin | [`runtimes/kt/`](../runtimes/kt) | `codeupipe-core` | Android, JVM, multiplatform |

### API Surface — quick reference

The idiomatic names differ by language, but the **shape** is identical.

| Concept | Python | TypeScript | Rust | Go | C# | Kotlin |
|---|---|---|---|---|---|---|
| Read | `p.get("k")` | `p.get("k")` | `p.get("k")` | `p.Get("k")` | `p.Get("k")` | `p.get("k")` |
| Write | `p.insert("k", v)` | `p.insert("k", v)` | `p.insert("k", v)` | `p.Insert("k", v)` | `p.Insert("k", v)` | `p.insert("k", v)` |
| Add filter | `pipe.add_filter(F())` | `pipe.addFilter(F)` | `pipe.add_filter(F)` | `pipe.AddFilter(f)` | `pipe.AddFilter(f)` | `pipe.addFilter(f)` |
| Run | `pipe.run(p)` | `await pipe.run(p)` | `pipe.run(p)?` | `pipe.Run(p)` | `pipe.Run(p)` | `pipe.run(p)` |

---

## 7. Language-Agnostic Pseudocode Patterns

### 7.1 A single Filter

```
filter CleanText:
  input:  Payload with "raw_text": string
  output: Payload with "text": string; "raw_text" preserved
  body:
    text ← trim(payload.get("raw_text"))
    return payload.insert("text", text)
```

### 7.2 A conditional Filter (Valve pattern)

```
valve WhenPremium gates ChargeUser:
  predicate(payload) → boolean:
    return payload.get("subscription_type") == "premium"

pipeline Billing:
  steps:
    - Authenticate
    - WhenPremium(ChargeUser)
    - RecordInvoice
```

### 7.3 A Pipeline with observation

```
pipeline UserIngestion:
  steps:
    - AuthenticateUser
    - WhenHasPhone(NormalizePhone)
    - WriteToDatabase

tap PublishUserRegistered observes WriteToDatabase:
  on_payload(payload):
    async_dispatch(
      event_bus.publish("user.registered", {
        "user_id": payload.get("user_id"),
        "email":   payload.get("email"),
      })
    )

hook TimingHook:
  before(name, payload, state):
    state.filter_timings[name] ← now()
  after(name, payload, state):
    state.filter_timings[name] ← now() - state.filter_timings[name]
```

### 7.4 Error handling with a Hook

```
hook RetryPolicy(max_attempts = 3):
  on_error(name, payload, error, state):
    state.retries[name] ← (state.retries[name] or 0) + 1
    if state.retries[name] < max_attempts:
      return retry
    else:
      return propagate
```

---

## 8. The Anti-Pattern Checklist

When reviewing code, look for these — every one is a Manifesto violation.

- [ ] `if/else` inside a Filter that changes routing → **use a Valve**.
- [ ] `payload._data[…] = …` or any in-place Payload edit → **use `insert`**.
- [ ] Payload carrying `_step_count`, `_started_at`, `_errors` → **that's State**.
- [ ] Filter reading State → **Filters are blind to State by contract**.
- [ ] Tap that mutates the Payload → **that's a Filter, not a Tap**.
- [ ] Tap doing synchronous HTTP / DB writes on the hot path → **async handoff**.
- [ ] Tap raising into the Pipeline → **Taps swallow their own errors**.
- [ ] Hook that transforms domain data silently → **that's a Filter, not a Hook**.
- [ ] `before` Hook trying to enrich the Payload → **put a Filter in front**.
- [ ] Multiple responsibilities in one Filter → **split into two Filters**.
- [ ] Filter returning something other than a Payload → **contract violation**.
- [ ] Filter with hidden global state → **inject as constructor config**.

---

## 9. Test Contract

Every Filter must be **unit-testable in isolation** with no mocks:

```
payload  ← Payload({ "raw_text": "  hi  " })
result   ← CleanText().call(payload)
assert result.get("text") == "hi"
assert payload.get("text") == null   # original unchanged
```

Every Pipeline must be **runnable twice with the same input** and produce
identical output — regardless of Taps or Hooks.

---

## 10. The "Orchie" Review Voice

When reviewing CUP code, adopt this stance (paraphrased from the SME persona):

- **Empathetic:** "I completely see why you'd want to just mutate that in place — it feels faster right now."
- **Trust but verify:** "Hold on, let me check the T0 contract on Taps to make sure we aren't violating the pure read-only constraint."
- **Blueprint-first:** "Let's zoom out and look at the Pipeline blueprint before we discuss what the Filter does."
- **Vocabulary discipline:** "Valves *gate*. Taps *observe*. Hooks *fire*. State is the *clipboard*, Payload is the *envelope*."

---

## 11. Where to Find Things

- **Landing page** (this file's neighbor): [`index.html`](./index.html)
- **Live runtime** (compiled TS): [`runtime/`](./runtime)
- **Full source**: <https://github.com/orchestrate-solutions/codeupipe>
- **Canonical Python**: [`codeupipe/core/`](../codeupipe/core)
- **All runtimes**: [`runtimes/`](../runtimes)

---

## 12. When You Are Uncertain

Do what Orchie does: **do not trust your memory**. Re-read the relevant primitive's
section in this file before answering. If your answer would violate any invariant
in Section 4 or trip any item in the checklist in Section 8, revise.

The Manifesto is short. The contracts are short. The invariants are short.
Re-reading them is faster than debugging a violation.
