// A pipeline over a type of your own. Payload is the default, a map that any
// developer can read; a class can take its place. The Pipeline asks one
// thing of it, copy(), for the copy that a run works on. Lineage is kept only
// by a type that has _stamp(label); for any other type it does nothing.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Hook, Payload, Pipeline } from "../src/index.ts";
import type { Filter, PipelineData, Predicate, Tap } from "../src/index.ts";

class Order implements PipelineData<Order> {
  price: number;
  qty: number;
  bulk: boolean;

  constructor(price: number, qty: number, bulk = false) {
    this.price = price;
    this.qty = qty;
    this.bulk = bulk;
  }

  copy(): Order {
    return new Order(this.price, this.qty, this.bulk);
  }
}

class TracedOrder extends Order {
  steps: string[] = [];

  override copy(): TracedOrder {
    const copy = new TracedOrder(this.price, this.qty, this.bulk);
    copy.steps = [...this.steps];
    return copy;
  }

  _stamp(label: string): void {
    this.steps.push(label);
  }
}

class DiscountFilter implements Filter<Order> {
  call(order: Order): Order {
    order.price = Math.round(order.price * 90) / 100;
    return order;
  }
}

class MarkBulkFilter implements Filter<Order> {
  call(order: Order): Order {
    order.bulk = true;
    return order;
  }
}

class RefuseFreeFilter implements Filter<Order> {
  async call(order: Order): Promise<Order> {
    if (order.price <= 0) throw new Error("an order must cost something");
    return order;
  }
}

class PassTracedFilter implements Filter<TracedOrder> {
  call(order: TracedOrder): TracedOrder {
    return order;
  }
}

class MarkRanFilter implements Filter {
  call(payload: Payload): Payload {
    return payload.insert("ran", true);
  }
}

class AtLeastPredicate implements Predicate<Order> {
  test(order: Order): boolean {
    return order.qty >= 10;
  }
}

class SeeTap implements Tap<Order> {
  readonly seen: number[] = [];

  observe(order: Order): void {
    this.seen.push(order.price);
  }
}

class RecordHook extends Hook<Order> {
  readonly events: string[] = [];

  override before(step: string | null): void {
    this.events.push(`before:${step ?? ""}`);
  }

  override onError(step: string | null, _error: unknown, order: Order): void {
    this.events.push(`error:${step ?? ""}:${order.price}`);
  }
}

class PricingPipeline extends Pipeline<Order> {
  constructor() {
    super();
    this.addFilter(new DiscountFilter());
    this.addValve(new AtLeastPredicate(), new MarkBulkFilter());
  }
}

test("every primitive takes the type", async () => {
  const tap = new SeeTap();
  const hook = new RecordHook();
  const pipeline = new PricingPipeline();
  pipeline.addTap(tap);
  pipeline.useHook(hook);
  const given = new Order(100, 12);
  const out = await pipeline.run(given);
  assert.deepEqual(out, new Order(90, 12, true));
  assert.deepEqual(given, new Order(100, 12)); // the caller's value is not changed
  assert.deepEqual(tap.seen, [90]);
  assert.deepEqual(pipeline.state.executed, ["DiscountFilter", "MarkBulkFilter", "SeeTap"]);
  assert.deepEqual(hook.events, ["before:", "before:DiscountFilter", "before:MarkBulkFilter"]);
  await pipeline.run(new Order(100, 2));
  assert.deepEqual(pipeline.state.skipped, ["MarkBulkFilter"]);
});

test("a nested pipeline takes the type", async () => {
  const pipeline = new Pipeline<Order>();
  pipeline.addPipeline(new PricingPipeline());
  pipeline.addFilter(new RefuseFreeFilter());
  assert.deepEqual(await pipeline.run(new Order(50, 10)), new Order(45, 10, true));
});

test("a failure is the same as with a Payload", async () => {
  const hook = new RecordHook();
  const pipeline = new Pipeline<Order>();
  pipeline.addFilter(new DiscountFilter());
  pipeline.addFilter(new RefuseFreeFilter());
  pipeline.useHook(hook);
  await assert.rejects(pipeline.run(new Order(0, 1)), /must cost something/);
  assert.deepEqual(pipeline.state.executed, ["DiscountFilter"]);
  assert.deepEqual(hook.events.slice(-2), ["error:RefuseFreeFilter:0", "error::0"]);
});

test("lineage does nothing for a type without _stamp", async () => {
  const pipeline = new PricingPipeline();
  pipeline.observe({ lineage: true });
  assert.deepEqual(await pipeline.run(new Order(100, 12)), new Order(90, 12, true));
  assert.deepEqual(pipeline.state.executed, ["DiscountFilter", "MarkBulkFilter"]);
});

test("lineage is kept by a type with _stamp", async () => {
  const pipeline = new Pipeline<TracedOrder>();
  pipeline.addFilter(new PassTracedFilter());
  pipeline.observe({ lineage: true });
  const given = new TracedOrder(100, 12);
  const out = await pipeline.run(given);
  assert.deepEqual(out.steps, ["PassTracedFilter"]);
  assert.deepEqual(given.steps, []);
});

test("a Payload pipeline is still the default", async () => {
  const pipeline = new Pipeline();
  pipeline.addFilter(new MarkRanFilter());
  assert.deepEqual((await pipeline.run(new Payload())).toDict(), { ran: true });
});

// Checked by the type check (npm run typecheck), never run: a pipeline
// carries one type.
export function refusedByTheTypeCheck(): void {
  const payloads = new Pipeline();
  // @ts-expect-error A Filter of Order is not a Filter of Payload.
  payloads.addFilter(new DiscountFilter());
  const orders = new Pipeline<Order>();
  // @ts-expect-error A pipeline of Order does not run a Payload.
  void orders.run(new Payload());
  // @ts-expect-error A type of your own must have copy().
  void new Pipeline<{ price: number }>();
}
