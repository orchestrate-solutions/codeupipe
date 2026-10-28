import assert from "node:assert/strict";
import { test } from "node:test";

import { Hook, Payload, Pipeline, State } from "../src/index.ts";
import type { Filter, Predicate, Tap } from "../src/index.ts";

class AddFilter implements Filter {
  call(payload: Payload): Payload {
    return payload.insert("n", payload.get("n", 0) + 1);
  }
}

class AddLaterFilter implements Filter {
  async call(payload: Payload): Promise<Payload> {
    await Promise.resolve();
    return payload.insert("n", payload.get("n", 0) + 1);
  }
}

class FailFilter implements Filter {
  call(): Payload {
    throw new Error("boom");
  }
}

class IsOnPredicate implements Predicate {
  test(payload: Payload): boolean {
    return payload.get("on") === true;
  }
}

class SeeTap implements Tap {
  seen: unknown[] = [];
  observe(payload: Payload): void {
    this.seen.push(payload.get("n"));
  }
}

class FailTap implements Tap {
  observe(): void {
    throw new Error("sink is down");
  }
}

class FailLaterTap implements Tap {
  async observe(): Promise<void> {
    await Promise.resolve();
    throw new Error("sink is down later");
  }
}

class InnerPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new AddFilter());
    this.addFilter(new AddFilter());
  }
}

class RecordHook extends Hook {
  events: string[] = [];
  override before(step: string | null): void {
    this.events.push("before:" + (step ?? ""));
  }
  override after(step: string | null): void {
    this.events.push("after:" + (step ?? ""));
  }
  override onError(step: string | null): void {
    this.events.push("error:" + (step ?? ""));
  }
}

test("an empty pipeline returns the data it was given", async () => {
  const out = await new Pipeline().run(new Payload({ a: 1 }));
  assert.deepEqual(out.toDict(), { a: 1 });
});

test("steps run in order, and State records them", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addFilter(new AddLaterFilter());
  const out = await pipeline.run(new Payload({}));
  assert.equal(out.get("n"), 2);
  assert.deepEqual(pipeline.state.executed, ["AddFilter", "AddLaterFilter"]);
  assert.deepEqual(pipeline.state.skipped, []);
  assert.deepEqual(pipeline.state.errors, []);
});

test("run works on a copy: the caller's Payload is not changed", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  const given = new Payload({ n: 1 });
  const out = await pipeline.run(given);
  assert.equal(given.get("n"), 1);
  assert.equal(out.get("n"), 2);
});

test("a Valve runs its Filter when the Predicate is true", async () => {
  const pipeline = new Pipeline();
  pipeline.addValve(new IsOnPredicate(), new AddFilter());
  const out = await pipeline.run(new Payload({ on: true }));
  assert.equal(out.get("n"), 1);
  assert.deepEqual(pipeline.state.executed, ["AddFilter"]);
  assert.deepEqual(pipeline.state.skipped, []);
});

test("a Valve skips its Filter when the Predicate is false", async () => {
  const pipeline = new Pipeline();
  pipeline.addValve(new IsOnPredicate(), new AddFilter());
  const out = await pipeline.run(new Payload({ on: false }));
  assert.equal(out.has("n"), false);
  assert.deepEqual(pipeline.state.executed, []);
  assert.deepEqual(pipeline.state.skipped, ["AddFilter"]);
});

test("a Filter failure stops the run, and State keeps the steps before it", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addFilter(new FailFilter());
  pipeline.addFilter(new AddFilter());
  await assert.rejects(pipeline.run(new Payload({})), /boom/);
  assert.deepEqual(pipeline.state.executed, ["AddFilter"]);
});

test("a Tap reads the Payload and counts as executed", async () => {
  const tap = new SeeTap();
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addTap(tap);
  await pipeline.run(new Payload({}));
  assert.deepEqual(tap.seen, [1]);
  assert.deepEqual(pipeline.state.executed, ["AddFilter", "SeeTap"]);
});

test("a Tap failure is recorded and does not stop the run", async () => {
  const hook = new RecordHook();
  const pipeline = new Pipeline();
  pipeline.addTap(new FailTap());
  pipeline.addTap(new FailLaterTap());
  pipeline.addFilter(new AddFilter());
  pipeline.useHook(hook);
  const out = await pipeline.run(new Payload({}));
  assert.equal(out.get("n"), 1);
  assert.deepEqual(pipeline.state.executed, ["FailTap", "FailLaterTap", "AddFilter"]);
  assert.deepEqual(pipeline.state.errors.map(([label]) => label), ["FailTap", "FailLaterTap"]);
  assert.match(String(pipeline.state.errors[0]?.[1]), /sink is down/);
  assert.deepEqual(hook.events, ["before:", "before:AddFilter", "after:AddFilter", "after:"]);
});

test("a nested pipeline is one step", async () => {
  const pipeline = new Pipeline();
  pipeline.addPipeline(new InnerPipeline());
  pipeline.addFilter(new AddFilter());
  const out = await pipeline.run(new Payload({}));
  assert.equal(out.get("n"), 3);
  assert.deepEqual(pipeline.state.executed, ["InnerPipeline", "AddFilter"]);
});

test("Hooks see the pipeline and each Filter or Valve, in order", async () => {
  const hook = new RecordHook();
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addValve(new IsOnPredicate(), new AddLaterFilter());
  pipeline.addTap(new SeeTap());
  pipeline.useHook(hook);
  await pipeline.run(new Payload({}));
  assert.deepEqual(hook.events, [
    "before:", "before:AddFilter", "after:AddFilter",
    "before:AddLaterFilter", "after:AddLaterFilter", "after:",
  ]);
});

test("on a Filter failure a Hook gets the step, then the pipeline, and no after", async () => {
  const hook = new RecordHook();
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addFilter(new FailFilter());
  pipeline.useHook(hook);
  await assert.rejects(pipeline.run(new Payload({})));
  assert.deepEqual(hook.events, [
    "before:", "before:AddFilter", "after:AddFilter",
    "before:FailFilter", "error:FailFilter", "error:",
  ]);
});

test("a Hook gets the error itself", async () => {
  const seen: unknown[] = [];
  class KeepErrorHook extends Hook {
    override onError(_step: string | null, error: unknown): void {
      seen.push(error);
    }
  }
  const pipeline = new Pipeline();
  pipeline.addFilter(new FailFilter());
  pipeline.useHook(new KeepErrorHook());
  await assert.rejects(pipeline.run(new Payload({})));
  assert.equal(seen.length, 2);
  assert.ok(seen[0] instanceof Error);
  assert.equal(seen[0], seen[1]);
});

test("a Hook method can be async", async () => {
  const events: string[] = [];
  class SlowHook extends Hook {
    override async before(step: string | null): Promise<void> {
      await Promise.resolve();
      events.push("before:" + (step ?? ""));
    }
  }
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.useHook(new SlowHook());
  await pipeline.run(new Payload({}));
  assert.deepEqual(events, ["before:", "before:AddFilter"]);
});

test("timing and lineage are off by default", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  const out = await pipeline.run(new Payload({}));
  assert.equal(pipeline.state.timings.size, 0);
  assert.deepEqual(out.lineage, []);
});

test("observe turns timing on, and lineage when asked", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddFilter());
  pipeline.addTap(new SeeTap());
  pipeline.addValve(new IsOnPredicate(), new AddLaterFilter());
  pipeline.observe({ lineage: true });
  const out = await pipeline.run(new Payload({}));
  assert.deepEqual([...pipeline.state.timings.keys()], ["AddFilter", "AddLaterFilter"]);
  assert.ok((pipeline.state.timings.get("AddFilter") ?? -1) >= 0);
  assert.deepEqual(out.lineage, ["AddFilter", "AddLaterFilter"]);
});

test("each run starts with a new State", async () => {
  const pipeline = new Pipeline();
  pipeline.addValve(new IsOnPredicate(), new AddFilter());
  await pipeline.run(new Payload({ on: false }));
  await pipeline.run(new Payload({ on: true }));
  assert.deepEqual(pipeline.state.executed, ["AddFilter"]);
  assert.deepEqual(pipeline.state.skipped, []);
});

test("two runs at the same time do not write into the same State", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new AddLaterFilter());
  pipeline.addFilter(new AddLaterFilter());
  const [a, b] = await Promise.all([pipeline.run(new Payload({})), pipeline.run(new Payload({}))]);
  assert.equal(a.get("n"), 2);
  assert.equal(b.get("n"), 2);
  assert.deepEqual(pipeline.state.executed, ["AddLaterFilter", "AddLaterFilter#2"]);
});

// -- a State belongs to one run -------------------------------------------

class WaitFilter implements Filter {
  async call(payload: Payload): Promise<Payload> {
    await new Promise((resolve) => setTimeout(resolve, payload.get<number>("wait") ?? 0));
    return payload.insert("done", payload.get("name"));
  }
}

class FailForBFilter implements Filter {
  call(payload: Payload): Payload {
    if (payload.get("name") === "B") throw new Error("B fails");
    return payload;
  }
}

test("each of two runs at the same time writes into the State that its caller gave", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new WaitFilter());
  pipeline.addFilter(new FailForBFilter());
  const [a, b] = [new State(), new State()];
  // A starts first and ends last. B starts second, fails, and ends first.
  await Promise.all([
    pipeline.run(new Payload({ name: "A", wait: 40 }), a),
    pipeline.run(new Payload({ name: "B", wait: 5 }), b).catch(() => null),
  ]);
  assert.deepEqual(a.executed, ["WaitFilter", "FailForBFilter"]);
  assert.deepEqual(b.executed, ["WaitFilter"]);
  assert.equal(pipeline.state, b); // the State of the run that started last
});

test("with no State from the caller, a run makes a new one, and a later run does not write into a State that was given", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new FailForBFilter());
  const given = new State();
  await pipeline.run(new Payload({ name: "A" }), given);
  assert.equal(pipeline.state, given);
  await pipeline.run(new Payload({ name: "A" }));
  assert.notEqual(pipeline.state, given);
  assert.deepEqual(given.executed, ["FailForBFilter"]);
  assert.deepEqual(pipeline.state.executed, ["FailForBFilter"]);
});
