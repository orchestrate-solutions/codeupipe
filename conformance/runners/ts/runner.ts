// TypeScript conformance runner: executes cases, reports what happened.
//
//   bun run --preload runtimes/ts/identity/bun_preload.ts conformance/runners/ts/runner.ts \
//       [run|run_async|bench] < cases.json > results.json
//
// Runs the vendored runtimes/ts source directly (Bun strips types and maps
// the ".js" import specifiers to ".ts"), so it needs no npm install.
// Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
import { Payload, Pipeline, Valve } from "../../../runtimes/ts/src/index.ts";
import type { Filter, Hook, Predicate, Tap } from "../../../runtimes/ts/src/index.ts";

type Spec = Record<string, any>;

let taps: unknown[] = [];
let hooks: string[] = [];

// Every step is a top-level class: steps are identified by their stamped
// declaration (conformance/API.md, "Step identity"), and object literals or
// arrows have none. Run with identity/bun_preload.ts (see conformance/run.py).
class SetOp implements Filter {
  constructor(private key: string, private value: unknown) {}
  call(p: Payload) { return p.insert(this.key, this.value); }
}
class CopyOp implements Filter {
  constructor(private from: string, private to: string) {}
  call(p: Payload) { return p.insert(this.to, p.get(this.from)); }
}
class AddOp implements Filter {
  constructor(private key: string, private by: number) {}
  call(p: Payload) { return p.insert(this.key, (p.get(this.key, 0) as number) + this.by); }
}
class AppendOp implements Filter {
  constructor(private key: string, private value: unknown) {}
  call(p: Payload) { return p.insert(this.key, [...((p.get(this.key) as unknown[]) ?? []), this.value]); }
}
class RemoveOp implements Filter {
  constructor(private key: string) {}
  call(p: Payload) { return p.remove(this.key); }
}
class MergeOp implements Filter {
  constructor(private value: Spec) {}
  call(p: Payload) { return p.merge(new Payload(this.value)); }
}
class HasOp implements Filter {
  constructor(private key: string, private to: string) {}
  call(p: Payload) { return p.insert(this.to, p.has(this.key)); }
}
class MutateOp implements Filter {
  constructor(private key: string, private value: unknown) {}
  call(p: Payload) {
    const m = p.withMutation();
    m.set(this.key, this.value);
    return m.toImmutable();
  }
}
class FailOp implements Filter {
  constructor(private message: string) {}
  call(): Payload { throw new Error(this.message); }
}
class RecordTap implements Tap {
  constructor(private key: string) {}
  observe(p: Payload) { taps.push(p.get(this.key)); }
}
class FailTap implements Tap {
  constructor(private message: string) {}
  observe(): void { throw new Error(this.message); }
}
class NoopTap implements Tap {
  observe(): void {}
}
/** The runner's named pipeline type: nested pipelines must be named types. */
class Nested extends Pipeline {}

function filterFor(spec: Spec): Filter {
  switch (spec.op) {
    case "set": return new SetOp(spec.key, spec.value);
    case "copy": return new CopyOp(spec.from, spec.to);
    case "add": return new AddOp(spec.key, spec.by);
    case "append": return new AppendOp(spec.key, spec.value);
    case "remove": return new RemoveOp(spec.key);
    case "merge": return new MergeOp(spec.value);
    case "has": return new HasOp(spec.key, spec.to);
    case "mutate": return new MutateOp(spec.key, spec.value);
    case "fail": return new FailOp(spec.message);
  }
  throw new Unsupported(`unknown filter op ${spec.op}`);
}

function tapFor(spec: Spec): Tap {
  if (spec.op === "record") return new RecordTap(spec.key);
  if (spec.op === "fail") return new FailTap(spec.message);
  if (spec.op === "noop") return new NoopTap();
  throw new Unsupported(`unknown tap op ${spec.op}`);
}

function truthy(v: unknown): boolean {
  if (Array.isArray(v)) return v.length > 0;
  if (v && typeof v === "object") return Object.keys(v).length > 0;
  return Boolean(v);
}

// Valve predicates are objects (conformance/API.md, "Valve"): named classes
// with test(payload), the case's condition on the instance.
class EqualsWhen implements Predicate {
  constructor(private key: string, private value: unknown) {}
  test(p: Payload) { return JSON.stringify(p.get(this.key)) === JSON.stringify(this.value); }
}
class TruthyWhen implements Predicate {
  constructor(private key: string) {}
  test(p: Payload) { return truthy(p.get(this.key)); }
}

function whenFor(when: Spec): Predicate {
  if (when.op === "equals") return new EqualsWhen(when.key, when.value);
  if (when.op === "truthy") return new TruthyWhen(when.key);
  throw new Unsupported(`unknown valve op ${when.op}`);
}

class Unsupported extends Error {}

/** Build a case's steps. */
function build(steps: Spec[], nested = false): Pipeline {
  const p = nested ? new Nested() : new Pipeline();
  for (const s of steps) {
    if (s.kind === "filter") p.addFilter(filterFor(s));
    else if (s.kind === "tap") p.addTap(tapFor(s));
    else if (s.kind === "valve") p.addFilter(new Valve(filterFor(s.filter), whenFor(s.when)));
    else if (s.kind === "pipeline") p.addPipeline(build(s.steps, true));
    else throw new Unsupported(`unknown step kind ${s.kind}`);
  }
  return p;
}

/**
 * identity -> the case's step name. Steps are identified by their filter
 * (conformance/API.md); the shared cases name them. Each case step adds
 * exactly one pipeline step, in order, so the two lists line up. An identity
 * this map does not know stays as is and fails the comparison.
 */
function labels(p: Pipeline, steps: Spec[]): Map<string, string> {
  return new Map(p.identities.map((identity, i) => [identity, steps[i]!.name as string]));
}

const named = (xs: string[], label: Map<string, string>) => xs.map((x) => label.get(x) ?? x);

class RecordHook implements Hook {
  before(step: string | null) { hooks.push("before:" + (step ?? "")); }
  after(step: string | null) { hooks.push("after:" + (step ?? "")); }
  onError(step: string | null) { hooks.push("error:" + (step ?? "")); }
}

const MODE = process.argv[2] ?? "run";

async function runCase(c: Spec): Promise<Spec> {
  taps = [];
  hooks = [];
  let p: Pipeline;
  try {
    p = build(c.steps);
  } catch (e) {
    return { id: c.id, unsupported: String(e) };
  }
  const label = labels(p, c.steps);
  if (c.hooks === true) p.useHook(new RecordHook());
  const input = structuredClone(c.input ?? {});
  const result: Spec = { id: c.id };
  try {
    const out = MODE === "run_async" ? await p.runAsync(new Payload(input)) : p.run(new Payload(input));
    result.output = out.toDict();
  } catch (e) {
    result.error = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
  }
  const state = p.state;
  result.state = {
    executed: named([...state.executed], label),
    skipped: named([...state.skipped], label),
    errors: named(state.errors.map(([step]) => step), label),
  };
  if (c.hooks === true) {
    result.hooks = hooks.map((h) => {
      const [phase, step] = [h.slice(0, h.indexOf(":")), h.slice(h.indexOf(":") + 1)];
      return `${phase}:${label.get(step) ?? step}`;
    });
  }
  result.taps = taps;
  result.input_after = input;
  return result;
}

const BENCH_WARMUP = 20000;
const BENCH_RUNS = 20000;
const BENCH_REPEATS = 5;

/** Best of BENCH_REPEATS x BENCH_RUNS, in µs per run. */
class NoopHook implements Hook {
  before() {}
  after() {}
  onError() {}
}

async function bench(cases: Spec[]): Promise<Spec[]> {
  const out: Spec[] = [];
  for (const c of cases) {
    const p = build(c.steps);
    if (c.hooks === "noop") p.useHook(new NoopHook());
    const run = () => p.run(new Payload(structuredClone(c.input)));
    const output = run().toDict();
    for (let i = 0; i < BENCH_WARMUP; i++) run();
    let best = Infinity;
    for (let r = 0; r < BENCH_REPEATS; r++) {
      const t0 = Bun.nanoseconds();
      for (let i = 0; i < BENCH_RUNS; i++) run();
      best = Math.min(best, Bun.nanoseconds() - t0);
    }
    out.push({ id: c.id, us_per_run: best / BENCH_RUNS / 1000, output });
  }
  return out;
}

const cases: Spec[] = JSON.parse(await Bun.stdin.text());
if (MODE === "bench") {
  process.stdout.write(JSON.stringify(await bench(cases)));
} else {
  const results: Spec[] = [];
  for (const c of cases) results.push(await runCase(c));
  process.stdout.write(JSON.stringify(results));
}
