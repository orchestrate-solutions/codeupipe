import { describe, expect, it } from "vitest";
import {
  TypedFilter,
  TypedHook,
  TypedPipeline,
  TypedTap,
  TypedValve,
} from "../src/typed/index.js";

interface Ctx {
  n: number;
  flag?: boolean;
}

class Increment implements TypedFilter<Ctx> {
  readonly name = "inc";
  async call(ctx: Ctx): Promise<Ctx> {
    return { ...ctx, n: ctx.n + 1 };
  }
}

class Doubler implements TypedFilter<Ctx> {
  readonly name = "dbl";
  async call(ctx: Ctx): Promise<Ctx> {
    return { ...ctx, n: ctx.n * 2 };
  }
}

class Exploder implements TypedFilter<Ctx> {
  async call(_ctx: Ctx): Promise<Ctx> {
    throw new Error("boom");
  }
}

describe("TypedPipeline", () => {
  it("empty pipeline passes ctx through", async () => {
    const pipe = new TypedPipeline<Ctx>();
    expect(await pipe.run({ n: 42 })).toEqual({ n: 42 });
  });

  it("single filter transforms", async () => {
    const pipe = new TypedPipeline<Ctx>().addFilter(new Increment(), "inc");
    expect((await pipe.run({ n: 0 })).n).toBe(1);
  });

  it("chained filters apply in order", async () => {
    const pipe = new TypedPipeline<Ctx>()
      .addFilter(new Increment(), "inc")
      .addFilter(new Doubler(), "dbl");
    // (3 + 1) * 2 = 8
    expect((await pipe.run({ n: 3 })).n).toBe(8);
  });

  it("tap observes without mutating", async () => {
    const seen: number[] = [];
    class Peek implements TypedTap<Ctx> {
      observe(ctx: Ctx) {
        seen.push(ctx.n);
      }
    }
    const pipe = new TypedPipeline<Ctx>()
      .addFilter(new Increment(), "inc")
      .addTap(new Peek(), "peek");
    const out = await pipe.run({ n: 10 });
    expect(out.n).toBe(11);
    expect(seen).toEqual([11]);
  });

  it("disabled tap marks skipped", async () => {
    const seen: number[] = [];
    class Peek implements TypedTap<Ctx> {
      observe(ctx: Ctx) {
        seen.push(ctx.n);
      }
    }
    const pipe = new TypedPipeline<Ctx>()
      .addTap(new Peek(), "peek")
      .disableTaps("peek");
    await pipe.run({ n: 5 });
    expect(seen).toEqual([]);
    expect(pipe.state.skipped).toContain("peek");
  });

  it("valve runs when predicate true", async () => {
    const valve = new TypedValve<Ctx>(new Increment(), (c) => c.flag === true);
    const pipe = new TypedPipeline<Ctx>().addFilter(valve, "gated");
    expect((await pipe.run({ n: 5, flag: true })).n).toBe(6);
  });

  it("valve skips when predicate false", async () => {
    const valve = new TypedValve<Ctx>(new Increment(), (c) => c.flag === true);
    const pipe = new TypedPipeline<Ctx>().addFilter(valve, "gated");
    const out = await pipe.run({ n: 5, flag: false });
    expect(out.n).toBe(5);
    expect(pipe.state.skipped).toContain("gated");
  });

  it("hooks fire for each filter step", async () => {
    const events: string[] = [];
    class Recorder implements TypedHook<Ctx> {
      before(step: string | undefined) {
        if (step) events.push(`before:${step}`);
      }
      after(step: string | undefined) {
        if (step) events.push(`after:${step}`);
      }
    }
    const pipe = new TypedPipeline<Ctx>()
      .addFilter(new Increment(), "inc")
      .addFilter(new Doubler(), "dbl")
      .useHook(new Recorder());
    await pipe.run({ n: 1 });
    expect(events).toEqual([
      "before:inc",
      "after:inc",
      "before:dbl",
      "after:dbl",
    ]);
  });

  it("error hook fires and re-raises", async () => {
    const caught: Array<{ step: string | undefined; msg: string }> = [];
    class ErrHook implements TypedHook<Ctx> {
      onError(step: string | undefined, err: Error) {
        caught.push({ step, msg: err.message });
      }
    }
    const pipe = new TypedPipeline<Ctx>()
      .addFilter(new Exploder(), "boom")
      .useHook(new ErrHook());
    await expect(pipe.run({ n: 0 })).rejects.toThrow("boom");
    expect(caught).toEqual([{ step: "boom", msg: "boom" }]);
  });

  it("removing taps yields identical output (invariant #1)", async () => {
    class Peek implements TypedTap<Ctx> {
      observe(_ctx: Ctx) {
        /* noop */
      }
    }
    const withTap = new TypedPipeline<Ctx>()
      .addFilter(new Increment(), "inc")
      .addTap(new Peek(), "peek")
      .addFilter(new Doubler(), "dbl");
    const withoutTap = new TypedPipeline<Ctx>()
      .addFilter(new Increment(), "inc")
      .addFilter(new Doubler(), "dbl");
    expect(await withTap.run({ n: 3 })).toEqual(await withoutTap.run({ n: 3 }));
  });

  it("same ctx same pipe same output (invariant #2)", async () => {
    const build = () =>
      new TypedPipeline<Ctx>()
        .addFilter(new Increment(), "inc")
        .addFilter(new Doubler(), "dbl");
    const a = await build().run({ n: 7 });
    const b = await build().run({ n: 7 });
    expect(a).toEqual(b);
  });

  it("dict escape hatch: Ctx as Record<string, unknown>", async () => {
    class DictInc implements TypedFilter<Record<string, unknown>> {
      async call(ctx: Record<string, unknown>) {
        return { ...ctx, n: ((ctx.n as number) ?? 0) + 1 };
      }
    }
    const pipe = new TypedPipeline<Record<string, unknown>>().addFilter(
      new DictInc(),
      "inc",
    );
    const out = await pipe.run({ n: 10 });
    expect(out).toEqual({ n: 11 });
  });
});
