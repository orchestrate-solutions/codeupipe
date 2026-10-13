# Conformance matrix

A snapshot of `python conformance/run.py`. Regenerate with that command; the
live copy is `results/latest.md` (not committed). The command exits non-zero
if any target has a ❌.

**Every target passes every case, and nothing is unsupported.** The targets
are the Python dynamic run, async run and three compiled forms, and the
TypeScript run and its compiled form.

The fast modes (`python:static-steps`, `python:static-inline`,
`typescript:static`) expose no State or Hooks, so they pass those cases as
✅\*. `static-observe` (compile with
`observe=True`) records both and passes every case outright, but for one:
the case that asks for `state` on the Pipeline object. A compiled form is a
function and has no such object. See
[docs/compile.md](../docs/compile.md).

| case | python:run | python:run_async | python:static-steps | python:static-inline | python:static-observe | typescript:run | typescript:static |
|---|---|---|---|---|---|---|---|
| `hook/lifecycle-on-success` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `hook/on-error-when-a-filter-fails` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `hook/not-notified-of-a-tap-failure` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `hook/on-error-names-a-failing-valve` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `payload/insert-adds-a-key` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/insert-overwrites` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/missing-key-reads-as-null` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/nested-input-is-never-mutated` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/json-value-types-round-trip` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/remove-drops-a-key` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/remove-of-a-missing-key-is-a-no-op` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/merge-right-side-wins` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/has-reports-presence-even-for-null` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/mutable-escape-hatch-sets-in-place` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pipeline/empty-returns-input` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `pipeline/steps-run-in-order` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `pipeline/filter-error-halts-the-run` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `pipeline/nested-pipeline-is-a-step` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `state/the-caller-gives-the-state-of-a-run` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `state/a-run-that-starts-inside-another-run-has-its-own-state` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `state/with-no-state-from-the-caller-the-pipeline-has-the-state-of-the-run-that-started-last` | ✅ | ✅ | ✅* | ✅* | ✅* | ✅ | ✅* |
| `tap/observes-without-changing-output` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/failure-never-halts-the-pipeline` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/failure-does-not-stop-later-taps` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/sees-payload-after-a-skipped-valve` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/runs-when-predicate-true` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/skips-when-predicate-false` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/missing-key-is-falsy` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/sees-upstream-changes` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/independent-gates` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |

- **python:run**: 30 pass, 0 pass*, 0 fail, 0 unsupported
- **python:run_async**: 30 pass, 0 pass*, 0 fail, 0 unsupported
- **python:static-steps**: 11 pass, 19 pass*, 0 fail, 0 unsupported
- **python:static-inline**: 11 pass, 19 pass*, 0 fail, 0 unsupported
- **python:static-observe**: 29 pass, 1 pass*, 0 fail, 0 unsupported
- **typescript:run**: 30 pass, 0 pass*, 0 fail, 0 unsupported
- **typescript:static**: 11 pass, 19 pass*, 0 fail, 0 unsupported

✅* passed everything the target can observe; it does not expose State or Hooks (the fast mode). ➖ the target cannot express the case.
