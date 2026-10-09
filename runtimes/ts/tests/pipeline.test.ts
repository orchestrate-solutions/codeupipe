import { describe, it, expect } from "vitest";
import { Payload } from "../src/payload.js";
import { Pipeline } from "../src/pipeline.js";
import type { Filter } from "../src/filter.js";
import type { StreamFilter } from "../src/stream_filter.js";
import type { Tap } from "../src/tap.js";
import type { Hook } from "../src/hook.js";
import type { Predicate } from "../src/predicate.js";
import { Valve } from "../src/valve.js";
import { AsyncStepInSyncRun } from "../src/async_step_in_sync_run.js";

// --- Test filters ---

class AddOne implements Filter {
  async call(payload: Payload): Promise<Payload> {
    const x = (payload.get("x") as number) ?? 0;
    return payload.insert("x", x + 1);
  }
}

class MultiplyTwo implements Filter {
  async call(payload: Payload): Promise<Payload> {
    const x = (payload.get("x") as number) ?? 0;
    return payload.insert("x", x * 2);
  }
}

class SetKey implements Filter {
  constructor(
    private key: string,
    private value: unknown,
  ) {}
  async call(payload: Payload): Promise<Payload> {
    return payload.insert(this.key, this.value);
  }
}

class FailFilter implements Filter {
  async call(_payload: Payload): Promise<Payload> {
    throw new Error("intentional failure");
  }
}

// Sync filter (no explicit async)
class SyncAddOne implements Filter {
  async call(payload: Payload): Promise<Payload> {
    const x = (payload.get("x") as number) ?? 0;
    return payload.insert("x", x + 1);
  }
}

// --- Test stream filter ---

class SplitChunks implements StreamFilter {
  async *stream(chunk: Payload): AsyncIterable<Payload> {
    const text = chunk.get("text") as string;
    for (const word of text.split(" ")) {
      yield chunk.insert("word", word);
    }
  }
}

class DropFilter implements StreamFilter {
  async *stream(_chunk: Payload): AsyncIterable<Payload> {
    // yields nothing — drops the chunk
  }
}

// --- Test tap ---

class RecordingTap implements Tap {
  observed: Payload[] = [];
  async observe(payload: Payload): Promise<void> {
    this.observed.push(payload);
  }
}

// --- Test hook ---

class RecordingHook implements Hook {
  calls: string[] = [];
  async before(step: string | null, _payload: Payload): Promise<void> {
    this.calls.push(`before:${step ?? "pipeline"}`);
  }
  async after(step: string | null, _payload: Payload): Promise<void> {
    this.calls.push(`after:${step ?? "pipeline"}`);
  }
  async onError(
    _step: string | null,
    error: Error,
    _payload: Payload,
  ): Promise<void> {
    this.calls.push(`error:${error.message}`);
  }
}

// Step identities (conformance/API.md): stamped by identity/vite_plugin.ts.
const id = (name: string): string => `@codeupipe/core/tests/pipeline.test#${name}`;

/** A named pipeline type: only named Pipeline subclasses can be nested. */
class SubPipeline extends Pipeline {}

class IsBig implements Predicate {
  test(p: Payload): boolean {
    return (p.get("x") as number) > 10;
  }
}

class BoomTap implements Tap {
  observe(): void {
    throw new Error("sink down");
  }
}

class SyncInc implements Filter {
  call(p: Payload): Payload {
    return p.insert("n", ((p.get("n", 0) as number) + 1));
  }
}

/** A sync call that returns a Promise: run() must refuse it. */
class SneakyAsync implements Filter {
  call(p: Payload): Payload {
    return Promise.resolve(p) as unknown as Payload;
  }
}

// --- Tests ---

describe("Pipeline — batch execution", () => {
  it("runs empty pipeline", async () => {
    const pipeline = new Pipeline();
    const result = await pipeline.runAsync(new Payload({ x: 1 }));
    expect(result.get("x")).toBe(1);
  });

  it("runs single filter", async () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    const result = await pipeline.runAsync(new Payload({ x: 0 }));
    expect(result.get("x")).toBe(1);
    expect(pipeline.state.executed).toEqual([id("AddOne")]);
  });

  it("runs multiple filters in sequence", async () => {
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addFilter(new MultiplyTwo());
    const result = await pipeline.runAsync(new Payload({ x: 5 }));
    // (5 + 1) * 2 = 12
    expect(result.get("x")).toBe(12);
    expect(pipeline.state.executed).toEqual([id("AddOne"), id("MultiplyTwo")]);
  });

  it("tracks tap execution", async () => {
    const tap = new RecordingTap();
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addTap(tap);
    const result = await pipeline.runAsync(new Payload({ x: 0 }));
    expect(result.get("x")).toBe(1);
    expect(tap.observed).toHaveLength(1);
    expect(tap.observed[0]!.get("x")).toBe(1);
    expect(pipeline.state.executed).toEqual([id("AddOne"), id("RecordingTap")]);
  });

  it("disables taps", async () => {
    const tap = new RecordingTap();
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addTap(tap)
      .disableTaps(id("RecordingTap"));
    await pipeline.runAsync(new Payload({ x: 0 }));
    expect(tap.observed).toHaveLength(0);
    expect(pipeline.state.skipped).toEqual([id("RecordingTap")]);
  });

  it("re-enables taps", async () => {
    const tap = new RecordingTap();
    const pipeline = new Pipeline()
      .addTap(tap)
      .disableTaps(id("RecordingTap"))
      .enableTaps(id("RecordingTap"));
    await pipeline.runAsync(new Payload({ x: 0 }));
    expect(tap.observed).toHaveLength(1);
  });

  it("valve executes when predicate true", async () => {
    const valve = new Valve(new MultiplyTwo(), new IsBig());
    const pipeline = new Pipeline().addFilter(valve);
    const result = await pipeline.runAsync(new Payload({ x: 20 }));
    expect(result.get("x")).toBe(40);
    expect(pipeline.state.executed).toEqual([id("MultiplyTwo")]);
  });

  it("valve skips when predicate false", async () => {
    const valve = new Valve(new MultiplyTwo(), new IsBig());
    const pipeline = new Pipeline().addFilter(valve);
    const result = await pipeline.runAsync(new Payload({ x: 5 }));
    expect(result.get("x")).toBe(5); // unchanged
    expect(pipeline.state.skipped).toEqual([id("MultiplyTwo")]);
  });

  it("hooks fire in order", async () => {
    const hook = new RecordingHook();
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .useHook(hook);
    await pipeline.runAsync(new Payload({ x: 0 }));
    expect(hook.calls).toEqual([
      "before:pipeline",
      `before:${id("AddOne")}`, // hooks receive the step's identity (API contract)
      `after:${id("AddOne")}`,
      "after:pipeline",
    ]);
  });

  it("hooks fire onError", async () => {
    const hook = new RecordingHook();
    const pipeline = new Pipeline()
      .addFilter(new FailFilter())
      .useHook(hook);
    await expect(pipeline.runAsync(new Payload({}))).rejects.toThrow(
      "intentional failure",
    );
    expect(hook.calls).toContain("error:intentional failure");
  });

  it("parallel fan-out/fan-in", async () => {
    const pipeline = new Pipeline().addParallel(
      [new SetKey("a", 1), new SetKey("b", 2)],
    );
    const result = await pipeline.runAsync(new Payload({}));
    expect(result.get("a")).toBe(1);
    expect(result.get("b")).toBe(2);
    expect(pipeline.state.executed).toEqual([`parallel[${id("SetKey")},${id("SetKey")}]`]);
  });

  it("nested pipeline", async () => {
    const inner = new SubPipeline()
      .addFilter(new AddOne());
    const outer = new Pipeline()
      .addFilter(new MultiplyTwo())
      .addPipeline(inner);
    const result = await outer.runAsync(new Payload({ x: 3 }));
    // 3 * 2 = 6, then 6 + 1 = 7
    expect(result.get("x")).toBe(7);
    expect(outer.state.executed).toEqual([id("MultiplyTwo"), id("SubPipeline")]);
  });

  it("observe timing records durations", async () => {
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .observe({ timing: true });
    await pipeline.runAsync(new Payload({ x: 0 }));
    expect(pipeline.state.timings[id("AddOne")]).toBeDefined();
    expect(pipeline.state.timings[id("AddOne")]).toBeGreaterThanOrEqual(0);
  });

  it("observe lineage stamps steps", async () => {
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addFilter(new MultiplyTwo())
      .observe({ lineage: true });
    const result = await pipeline.runAsync(new Payload({ x: 0 }));
    expect(result.lineage).toEqual([id("AddOne"), id("MultiplyTwo")]);
  });

  it("rejects StreamFilter in batch mode", async () => {
    const pipeline = new Pipeline().addFilter(
      new SplitChunks() as unknown as Filter,
    );
    await expect(pipeline.runAsync(new Payload({ text: "a b" }))).rejects.toThrow(
      "StreamFilter",
    );
  });

  it("error propagates and state has error timing", async () => {
    const pipeline = new Pipeline()
      .addFilter(new FailFilter())
      .observe({ timing: true });
    await expect(pipeline.runAsync(new Payload({}))).rejects.toThrow(
      "intentional failure",
    );
    expect(pipeline.state.timings[id("FailFilter")]).toBeDefined();
  });

  it("state resets between runs", async () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    await pipeline.runAsync(new Payload({ x: 0 }));
    expect(pipeline.state.executed).toEqual([id("AddOne")]);
    await pipeline.runAsync(new Payload({ x: 10 }));
    expect(pipeline.state.executed).toEqual([id("AddOne")]);
  });

  it("callAsync() is the async Filter protocol — enables nesting", async () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    const result = await pipeline.callAsync(new Payload({ x: 5 }));
    expect(result.get("x")).toBe(6);
  });
});

describe("Pipeline — describe", () => {
  it("describes empty pipeline", () => {
    const desc = new Pipeline().describe();
    expect(desc.steps).toEqual([]);
    expect(desc.hooks).toEqual([]);
    expect(desc.step_count).toBe(0);
  });

  it("describes filters and taps", () => {
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addTap(new RecordingTap());
    const desc = pipeline.describe();
    expect(desc.step_count).toBe(2);
    expect(desc.steps[0]!).toMatchObject({ name: id("AddOne"), type: "filter" });
    expect(desc.steps[1]!).toMatchObject({ name: id("RecordingTap"), type: "tap" });
  });

  it("describes parallel groups", () => {
    const pipeline = new Pipeline().addParallel(
      [new SetKey("a", 1), new SetKey("b", 2)],
    );
    const desc = pipeline.describe();
    expect(desc.steps[0]!).toMatchObject({
      name: `parallel[${id("SetKey")},${id("SetKey")}]`,
      type: "parallel",
    });
  });

  it("describes nested pipelines", () => {
    const inner = new SubPipeline().addFilter(new AddOne());
    const outer = new Pipeline().addPipeline(inner);
    const desc = outer.describe();
    expect(desc.steps[0]!).toMatchObject({ name: id("SubPipeline"), type: "pipeline" });
    expect((desc.steps[0] as Record<string, unknown>)["children"]).toBeDefined();
  });

  it("describes hooks", () => {
    const pipeline = new Pipeline().useHook(new RecordingHook());
    const desc = pipeline.describe();
    expect(desc.hooks).toEqual(["RecordingHook"]);
  });
});

describe("Pipeline — streaming", () => {
  async function collect(gen: AsyncIterable<Payload>): Promise<Payload[]> {
    const results: Payload[] = [];
    for await (const chunk of gen) {
      results.push(chunk);
    }
    return results;
  }

  async function* toAsyncIter(
    payloads: Payload[],
  ): AsyncGenerator<Payload> {
    for (const p of payloads) {
      yield p;
    }
  }

  it("streams through regular filter", async () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    const source = toAsyncIter([
      new Payload({ x: 1 }),
      new Payload({ x: 2 }),
      new Payload({ x: 3 }),
    ]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results.map((r) => r.get("x"))).toEqual([2, 3, 4]);
    expect(pipeline.state.chunksProcessed[id("AddOne")]).toBe(3);
  });

  it("streams through StreamFilter (fan-out)", async () => {
    const pipeline = new Pipeline().addFilter(
      new SplitChunks() as unknown as Filter,
    );
    const source = toAsyncIter([new Payload({ text: "hello world" })]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results.map((r) => r.get("word"))).toEqual(["hello", "world"]);
  });

  it("streams through drop filter", async () => {
    const pipeline = new Pipeline().addFilter(
      new DropFilter() as unknown as Filter,
    );
    const source = toAsyncIter([
      new Payload({ x: 1 }),
      new Payload({ x: 2 }),
    ]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results).toEqual([]);
  });

  it("streaming taps observe each chunk", async () => {
    const tap = new RecordingTap();
    const pipeline = new Pipeline().addTap(tap);
    const source = toAsyncIter([
      new Payload({ x: 1 }),
      new Payload({ x: 2 }),
    ]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results).toHaveLength(2);
    expect(tap.observed).toHaveLength(2);
    expect(pipeline.state.chunksProcessed[id("RecordingTap")]).toBe(2);
  });

  it("streaming disabled tap skips", async () => {
    const tap = new RecordingTap();
    const pipeline = new Pipeline()
      .addTap(tap)
      .disableTaps(id("RecordingTap"));
    const source = toAsyncIter([new Payload({ x: 1 })]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results).toHaveLength(1);
    expect(tap.observed).toHaveLength(0);
    expect(pipeline.state.skipped).toEqual([id("RecordingTap")]);
  });

  it("streaming hooks fire", async () => {
    const hook = new RecordingHook();
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .useHook(hook);
    const source = toAsyncIter([new Payload({ x: 0 })]);
    await collect(pipeline.streamAsync(source));
    expect(hook.calls).toContain("before:pipeline");
    expect(hook.calls).toContain("after:pipeline");
  });

  it("streaming error fires hook", async () => {
    const hook = new RecordingHook();
    const pipeline = new Pipeline()
      .addFilter(new FailFilter())
      .useHook(hook);
    const source = toAsyncIter([new Payload({})]);
    await expect(collect(pipeline.streamAsync(source))).rejects.toThrow(
      "intentional failure",
    );
    expect(hook.calls).toContain("error:intentional failure");
  });

  it("streaming parallel applies to each chunk", async () => {
    const pipeline = new Pipeline().addParallel(
      [new SetKey("a", 1), new SetKey("b", 2)],
    );
    const source = toAsyncIter([new Payload({}), new Payload({})]);
    const results = await collect(pipeline.streamAsync(source));
    expect(results).toHaveLength(2);
    for (const r of results) {
      expect(r.get("a")).toBe(1);
      expect(r.get("b")).toBe(2);
    }
  });

  it("streaming nested pipeline", async () => {
    const inner = new SubPipeline().addFilter(new AddOne());
    const outer = new Pipeline().addPipeline(inner);
    const source = toAsyncIter([
      new Payload({ x: 10 }),
      new Payload({ x: 20 }),
    ]);
    const results = await collect(outer.streamAsync(source));
    expect(results.map((r) => r.get("x"))).toEqual([11, 21]);
  });
});

describe("Pipeline — addFilter returns this (fluent)", () => {
  it("chaining works", () => {
    const pipeline = new Pipeline()
      .addFilter(new AddOne())
      .addFilter(new MultiplyTwo())
      .addTap(new RecordingTap())
      .useHook(new RecordingHook())
      .observe({ timing: true });
    expect(pipeline).toBeInstanceOf(Pipeline);
  });
});

// On a failure, onError fires for the failing step and then for the pipeline
// (null), mirroring before/after, which fire at both levels. Same contract in
// every runtime: conformance/cases/hook.json.
describe("Pipeline — onError contract", () => {
  class NamedHook implements Hook {
    calls: string[] = [];
    before(step: string | null) { this.calls.push(`before:${step ?? ""}`); }
    after(step: string | null) { this.calls.push(`after:${step ?? ""}`); }
    onError(step: string | null) { this.calls.push(`error:${step ?? ""}`); }
  }


  it("fires for the failing step, then the pipeline", async () => {
    const a = new SetKey("a", 1);
    const b = new FailFilter();
    const hook = new NamedHook();
    const pipeline = new Pipeline().addFilter(a).addFilter(b).useHook(hook);

    await expect(pipeline.runAsync(new Payload({}))).rejects.toThrow("intentional failure");

    expect(hook.calls).toEqual([
      "before:", `before:${id("SetKey")}`, `after:${id("SetKey")}`,
      `before:${id("FailFilter")}`, `error:${id("FailFilter")}`, "error:",
    ]);
  });

  it("names a failing nested pipeline", async () => {
    const inner = new SubPipeline().addFilter(new FailFilter());
    const hook = new NamedHook();
    const pipeline = new Pipeline().addPipeline(inner).useHook(hook);

    await expect(pipeline.runAsync(new Payload({}))).rejects.toThrow("intentional failure");

    const sub = id("SubPipeline");
    expect(hook.calls).toEqual(["before:", `before:${sub}`, `error:${sub}`, "error:"]);
  });
});

// Plane B: a Tap failure never halts the pipeline. The error is recorded in
// state.errors under the Tap's name and the Tap still counts as executed.
// Same contract in every runtime: conformance/cases/tap.json.
describe("Pipeline — Plane B tap isolation", () => {
  it("a throwing tap does not halt run()", async () => {
    const pipeline = new Pipeline()
      .addFilter(new SetKey("a", 1))
      .addTap(new BoomTap())
      .addFilter(new SetKey("b", 2));

    const result = await pipeline.runAsync(new Payload({}));

    expect(result.toDict()).toEqual({ a: 1, b: 2 });
    expect(pipeline.state.executed).toEqual([id("SetKey"), id("BoomTap"), id("SetKey#2")]);
    expect(pipeline.state.errors.map(([step]) => step)).toEqual([id("BoomTap")]);
  });

  it("a throwing tap does not halt stream()", async () => {
    const pipeline = new Pipeline().addTap(new BoomTap());
    async function* source() {
      for (let n = 0; n < 3; n++) yield new Payload({ n });
    }

    const seen: unknown[] = [];
    for await (const chunk of pipeline.streamAsync(source())) seen.push(chunk.get("n"));

    expect(seen).toEqual([0, 1, 2]);
    expect(pipeline.state.errors.map(([step]) => step)).toEqual([id("BoomTap"), id("BoomTap"), id("BoomTap")]);
  });
});

// A failed run still records the steps that succeeded before the failure
// (conformance: pipeline/filter-error-halts-the-run).
describe("Pipeline — state after a failed run", () => {
  it("records steps executed before the failure", async () => {
    const pipeline = new Pipeline()
      .addFilter(new SetKey("a", 1))
      .addFilter(new FailFilter());

    await expect(pipeline.runAsync(new Payload({}))).rejects.toThrow("intentional failure");

    expect(pipeline.state.executed).toEqual([id("SetKey")]);
  });
});

// The CUP API contract, TypeScript side (conformance/API.md): run() is
// synchronous and never awaits; runAsync() is opt-in.
describe("Pipeline — sync run() and runAsync()", () => {
  it("run() is synchronous", () => {
    const pipeline = new Pipeline().addFilter(new SyncInc());
    const out = pipeline.run(new Payload({ n: 1 }));
    expect(out.get("n")).toBe(2);
  });

  it("run() refuses an async step instead of awaiting it", () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    expect(() => pipeline.run(new Payload({ x: 0 }))).toThrow(AsyncStepInSyncRun);
  });

  it("run() refuses a sync function that returns a Promise", () => {
    const pipeline = new Pipeline().addFilter(new SneakyAsync());
    expect(() => pipeline.run(new Payload({}))).toThrow(AsyncStepInSyncRun);
  });

  it("runAsync() runs async steps", async () => {
    const pipeline = new Pipeline().addFilter(new AddOne());
    expect((await pipeline.runAsync(new Payload({ x: 0 }))).get("x")).toBe(1);
  });

  it("steps take no names (identity is the filter)", () => {
    // @ts-expect-error addFilter takes no name
    expect(() => new Pipeline().addFilter(new SyncInc(), "inc")).toThrow(TypeError);
  });

  it("a nested pipeline runs synchronously as one step", () => {
    const inner = new SubPipeline().addFilter(new SyncInc());
    const outer = new Pipeline().addFilter(new SyncInc()).addPipeline(inner);
    expect(outer.run(new Payload({ n: 0 })).get("n")).toBe(2);
    expect(outer.state.executed).toEqual([id("SyncInc"), id("SubPipeline")]);
  });
});

describe("Payload — remove and has", () => {
  it("remove returns a new payload; has sees null values", () => {
    const p = new Payload({ a: null, b: 2 });
    expect(p.has("a")).toBe(true);
    expect(p.has("zz")).toBe(false);
    expect(p.remove("a").toDict()).toEqual({ b: 2 });
    expect(p.has("a")).toBe(true);
  });

  it("MutablePayload removes in place", () => {
    const m = new Payload({ a: 1 }).withMutation();
    m.set("k", "v");
    m.remove("a");
    expect(m.toImmutable().toDict()).toEqual({ k: "v" });
  });
});
