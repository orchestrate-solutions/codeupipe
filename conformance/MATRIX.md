# Conformance matrix

A snapshot of `python conformance/run.py`. Regenerate with that command; the
live copy is `results/latest.md` (not committed). The command exits non-zero
if any target has a ❌.

**Every target passes every case, and nothing is unsupported.** The targets
are the Python dynamic run, async run and three static exports, and the
TypeScript run and its compiled form.

The fast exports (`python:static-steps`, `python:static-inline`,
`typescript:static`) expose no State or Hooks, so they pass those cases as
✅\*. `static-observe` (export with
`observe=True`) records both and passes every case outright. See
[docs/static-export.md](../docs/static-export.md).

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
| `tap/observes-without-changing-output` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/failure-never-halts-the-pipeline` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/failure-does-not-stop-later-taps` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `tap/sees-payload-after-a-skipped-valve` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/runs-when-predicate-true` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/skips-when-predicate-false` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/missing-key-is-falsy` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/sees-upstream-changes` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |
| `valve/independent-gates` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅* |

- **python:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **python:run_async**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **python:static-steps**: 11 pass, 16 pass*, 0 fail, 0 unsupported
- **python:static-inline**: 11 pass, 16 pass*, 0 fail, 0 unsupported
- **python:static-observe**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **typescript:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **typescript:static**: 11 pass, 16 pass*, 0 fail, 0 unsupported

✅* passed everything the target can observe; it does not expose State or Hooks (the fast static export). ➖ the target cannot express the case.
