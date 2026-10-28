import assert from "node:assert/strict";
import { test } from "node:test";

import { AuditTap } from "../examples/pricing/audit-tap.ts";
import { PricingPipeline } from "../examples/pricing/pricing-pipeline.ts";
import { Payload } from "../src/index.ts";

test("a large order gets the discount and the bulk mark", async () => {
  const pipeline = new PricingPipeline();
  const out = await pipeline.run(new Payload({ price: 100.0, qty: 12 }));
  assert.deepEqual(out.toDict(), { price: 90, qty: 12, bulk: true });
  assert.deepEqual(pipeline.state.executed, ["DiscountFilter", "MarkBulkFilter", "AuditTap"]);
  assert.deepEqual(pipeline.state.errors, []);
});

test("the Tap reads the Payload and prints it", (t) => {
  const log = t.mock.method(console, "log", () => {});
  assert.equal(new AuditTap().observe(new Payload({ price: 90 })), undefined);
  assert.deepEqual(log.mock.calls.map((call) => call.arguments), [["audit:", { price: 90 }]]);
});

test("a small order gets the discount only", async () => {
  const pipeline = new PricingPipeline();
  const out = await pipeline.run(new Payload({ price: 100.0, qty: 2 }));
  assert.deepEqual(out.toDict(), { price: 90, qty: 2 });
  assert.deepEqual(pipeline.state.skipped, ["MarkBulkFilter"]);
});
