---
title: "T0 — Filter"
concept_id: filter
primitive: filter
tier: T0
tags: [filter, transformation, pure]
created: 2026-07-19
summary: The atomic unit of work — one Payload in, one Payload out.
---

# Filter

## Prose

A **Filter** is the atomic unit of work in codeupipe. It has exactly one method — call it `call` — that takes a Payload and returns a Payload. That's the whole contract.

A Filter is pure-ish: given the same input Payload, it should produce the same output Payload. It does not mutate its input. It does not reach out to global state unless that reach is the *purpose* of the Filter (e.g. a Filter whose whole job is to read a file). Each Filter does **one** thing, named after what it does: `CleanText`, `ValidateSchema`, `StoreRecord`.

One class per file. PascalCase class name, snake_case file name. This is not a stylistic preference — it makes Filters discoverable, testable, and composable across a large codebase.

## Analogy

A Filter is a **station on a conveyor belt**. It opens the envelope (Payload), reads what it needs, seals a new envelope with its contribution added, and places it back on the belt. It does one thing. It does not know or care what came before or comes after.

## Pseudocode

```
filter CleanText:
    body:
        text ← trim(payload.get("raw_text"))
        return payload.insert("text", text)

filter ValidateEmail:
    body:
        email ← payload.get("email") or ""
        return payload.insert("email_valid", "@" ∈ email)
```

## Contract

- **Signature:** `call(payload: Payload) → Payload`
- **Purity:** same input Payload produces the same output Payload
- **Immutability:** the input Payload is not mutated; a new Payload is returned
- **Single responsibility:** one Filter, one job, one name that describes that job
- **Layout:** one class per file; PascalCase class, snake_case filename

### Invariants

- A Filter always returns a Payload (never `null`, never omitted)
- A Filter does not mutate its input Payload
- A Filter does not silently swallow errors

## Diagram

```mermaid
flowchart LR
    P1[Payload in] --> F["Filter<br/>(one job)"]
    F --> P2[Payload out]
    style F fill:#ffd,stroke:#a90
```

## QA

**Q:** What if my Filter needs two Payloads?
**A:** It doesn't. Merge the two inputs into a single Payload before the Filter runs.

**Q:** Can a Filter have configuration?
**A:** Yes — configuration is set on the Filter *instance* at construction time. The Payload carries per-invocation data; the Filter carries per-instance configuration.

**Q:** Can a Filter make an HTTP call or read a file?
**A:** Yes — that's a legitimate Filter (e.g. `FetchUserRecord`). If the side effect *is* the purpose, that's fine.

**Q:** Should I split validation and processing into separate Filters?
**A:** Yes. Two Filters with one job each are easier to test, reorder, and skip via a Valve.

## Anti-Patterns

**Branching inside a Filter**
```
// WRONG
filter ProcessUser:
    body:
        if payload.get("role") = "admin": <admin thing>
        else if payload.get("role") = "guest": <guest thing>

// RIGHT — use Valves and separate Filters
valve WhenAdmin gates ProcessAdmin: predicate = role == "admin"
```

**Mutating the input Payload**
```
// WRONG
payload._data["ts"] = now()

// RIGHT
return payload.insert("ts", now())
```

**Doing two jobs**
```
// WRONG
filter CleanValidateStore: body: ...

// RIGHT
pipeline TextProcessing:
    steps: [CleanText, ValidateText, StoreText]
```

**Returning something other than a Payload**
```
// WRONG
return payload.get("id")

// RIGHT
return payload.insert("extracted_id", payload.get("id"))
```
