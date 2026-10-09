# Lowering proof scorecard

Reproducible pass/fail evidence that the static export of a Pipeline
(`codeupipe.lower`) behaves like the dynamic `Pipeline.run`, stays isolated,
and costs no more than hand-written Python. Every number here comes from a
command below; nothing is asserted without one.

Run everything from the repo root, in the environment the main README sets up:

```bash
python -m scorecard.differential                   # item 1 + 4 (~1 min)
python -m pytest -q -p no:cacheprovider tests/scorecard
```

## 1. Random-pipeline differential testing (+ 4. isolation)

`scorecard/differential.py`, `--seed` and `--count` (default 20260927, 2000).

A seeded, stdlib-only generator (`case_gen.py`) writes random cases **in the
conformance case format**, so any failure is a case you can paste into
`conformance/cases/`. The vocabulary is the conformance runner's own
(`runner.build`, the `cup_ops` package), reused, not reimplemented: every filter op
(`set copy add append remove merge has mutate fail`), every tap op
(`record noop fail`), Valves (`equals`/`truthy`) around any filter op,
nested pipelines two deep (empty ones too), `hooks: true` on ~40%, keys
that are awkward in source (quotes, backslash, unicode, spaces), values of
every JSON type, `add` operands that raise, and ~5% long cases (up to 40
steps) that cross the Payload's overlay-flattening depth. `--hostile-rate`
(default 0.15) gives a share of cases step names that stress code
generation (builtins, the generated `run()`'s locals, duplicates,
non-identifiers).

Each case runs in four modes: dynamic (reference), fast export `steps`,
fast export `inline`, observable export (`observe=True`).

| check | steps | inline | observe |
|---|---|---|---|
| output, or error type + message, **type-strict** (`True` ≠ `1` ≠ `1.0`) and key order | ✓ | ✓ | ✓ |
| Tap records | ✓ | ✓ | ✓ |
| caller's input not mutated (deep compare) | ✓ | ✓ | ✓ |
| second run on a fresh copy identical to the first | ✓ | ✓ | ✓ |
| a hooked pipeline is refused (documented), then the unhooked one compared | ✓ | ✓ | |
| State: executed, skipped, errors (name + error), timing keys | | | ✓ |
| Hook event sequence, with a deep snapshot of the payload at every event | | | ✓ |
| `SOURCE_HOOKS` guard: `run()` without `hooks=` raises `TypeError` | | | ✓ |

**Verdicts.** *pass*: agrees on every check. *refused*: export raised
`UnsupportedFilterShape`, counted separately, never as a pass. *fail*: any
divergence, or an export that crashed (a `SyntaxError` on load is not a
refusal). Every distinct failure signature is shrunk (`minimize.py`) to a
minimal case and printed.

**Isolation (item 4)** is measured inside the same runs: the caller's input
is deep-compared after every run in every mode, and a second run on a fresh
copy must give the same result. A `SnapshotHook` (`snapshot_hook.py`) is
attached to the dynamic run and passed to the observable export's `run()`;
at each event it deep-copies the payload, because a Payload is written in
place and the object changes later by design.

Results: `results/differential-<seed>-<count>.{json,md}`.
