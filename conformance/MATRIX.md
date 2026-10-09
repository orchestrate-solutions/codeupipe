# Conformance matrix

Snapshot of `python conformance/run.py` across every runtime. Regenerate with
that command; the live copy is `results/latest.md` (gitignored). The command
exits non-zero if any target has a ❌.

**Every runtime passes every case, and nothing is unsupported.** All seven
runtimes implement the [API contract](API.md): one `Pipeline` with a
synchronous `run` (plus opt-in async where the runtime has async steps),
Hooks, `Valve(inner, predicate)`, recorded Tap failures, nested pipelines,
and the shared Payload vocabulary. Every runtime identifies steps by their
filter (API.md, "Step identity"); each runner maps the reported
identities back to the cases' step names, so a wrong or inconsistent
identity fails here.

Python's static export has three targets. The two fast ones
(`static-steps`, `static-inline`) expose no State or Hooks, so they pass
those cases as ✅\*. `static-observe` (export with `observe=True`) records
both and passes every case outright. See
[docs/static-export.md](../docs/static-export.md).

| case | python:run | python:run_async | python:static-steps | python:static-inline | python:static-observe | go:run | ts:run | ts:run_async | cpp:run | kt:run | cs:run | rs:run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `hook/lifecycle-on-success` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `hook/on-error-when-a-filter-fails` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `hook/not-notified-of-a-tap-failure` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `hook/on-error-names-a-failing-valve` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/insert-adds-a-key` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/insert-overwrites` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/missing-key-reads-as-null` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/nested-input-is-never-mutated` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/json-value-types-round-trip` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/remove-drops-a-key` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/remove-of-a-missing-key-is-a-no-op` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/merge-right-side-wins` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/has-reports-presence-even-for-null` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `payload/mutable-escape-hatch-sets-in-place` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pipeline/empty-returns-input` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pipeline/steps-run-in-order` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pipeline/filter-error-halts-the-run` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pipeline/nested-pipeline-is-a-step` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tap/observes-without-changing-output` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tap/failure-never-halts-the-pipeline` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tap/failure-does-not-stop-later-taps` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `tap/sees-payload-after-a-skipped-valve` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/runs-when-predicate-true` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/skips-when-predicate-false` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/missing-key-is-falsy` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/sees-upstream-changes` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `valve/independent-gates` | ✅ | ✅ | ✅* | ✅* | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

- **python:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **python:run_async**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **python:static-steps**: 11 pass, 16 pass*, 0 fail, 0 unsupported
- **python:static-inline**: 11 pass, 16 pass*, 0 fail, 0 unsupported
- **python:static-observe**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **go:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **ts:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **ts:run_async**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **cpp:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **kt:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **cs:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported
- **rs:run**: 27 pass, 0 pass*, 0 fail, 0 unsupported

✅* passed everything the target can observe; it does not expose State or Hooks (the fast static export). ➖ the target cannot express the case.

## Each runtime's own test suite

| Runtime | Command |
|---|---|
| Python | `python -m pytest tests` |
| Go | `cd runtimes/go && go test ./...` |
| Rust | `cd runtimes/rs && cargo test` |
| TypeScript | `cd runtimes/ts && bun test` (or `vitest run`); `tsc --noEmit` |
| Kotlin | `runtimes/kt/test-local.sh` (kotlinc + JUnit; the Gradle build cannot run on current toolchains) |
| C# | `cd runtimes/cs && dotnet test CupPipe.Tests` |
| C++ | `cmake -S runtimes/cpp -B runtimes/cpp/build && cmake --build runtimes/cpp/build && runtimes/cpp/build/cup_tests` |
