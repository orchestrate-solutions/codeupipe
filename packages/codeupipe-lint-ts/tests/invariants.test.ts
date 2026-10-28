import assert from "node:assert/strict";
import { test } from "node:test";

import { lintIn } from "./lint-in.ts";

test("CUP-I003: a Filter or a Predicate that reads State", async () => {
  const out = await lintIn({
    "count-filter.ts": `import type { Payload, Pipeline, State } from "codeupipe";
export class CountFilter {
  pipeline: Pipeline;
  seen: State;
  state = 3;
  constructor(pipeline: Pipeline, seen: State) {
    this.pipeline = pipeline;
    this.seen = seen;
  }
  call(payload: Payload): Payload {
    payload.insert("a", this.pipeline.state.executed.length);
    payload.insert("b", this.seen.skipped);
    payload.insert("c", this.state);
    payload.insert("d", payload.get("state"));
    return payload;
  }
}
`,
    "ran-predicate.ts": `export class RanPredicate {
  holder;
  constructor(holder) { this.holder = holder; }
  test(payload) { return this.holder.state.executed.length > 0; }
}
`,
    "watch-tap.ts": `export class WatchTap {
  pipeline;
  observe(payload) { console.log(this.pipeline.state.executed); }
}
`,
  });
  assert.deepEqual(out.found, ["count-filter.ts:11 CUP-I003", "count-filter.ts:12 CUP-I003", "ran-predicate.ts:4 CUP-I003"]);
});

test("CUP-I004: a write to the Payload from a Tap, a Predicate or a Hook", async () => {
  const out = await lintIn({
    "mark-tap.ts": `export class MarkTap {
  rows = [];
  observe(payload) {
    payload.insert("seen", true).remove("x");
    payload.copy().insert("mine", 1);
    this.rows.insert(0, payload.get("a"));
  }
}
`,
    "is-new-predicate.ts": `export class IsNewPredicate {
  test(p) { p.withTrace("t"); return true; }
}
`,
    "stamp-hook.ts": `import { Hook } from "codeupipe";
export class StampHook extends Hook {
  override before(step, payload) { payload.merge(payload); }
  override onError(step, error, payload) { payload.insert("failed", true); }
}
`,
    "set-filter.ts": `export class SetFilter {
  call(payload) { return payload.insert("a", 1); }
}
`,
  });
  assert.deepEqual(out.found, ["is-new-predicate.ts:2 CUP-I004", "mark-tap.ts:4 CUP-I004",
    "stamp-hook.ts:3 CUP-I004", "stamp-hook.ts:4 CUP-I004"]);
  assert.match(out.findings[1]?.message ?? "", /^`observe` writes to the Payload \(`payload\.remove`\)\./);
});

test("CUP-I005: one primitive in each file", async () => {
  const out = await lintIn({
    "set-filter.ts": `export class SetFilter { call(payload) { return payload; } }
class Helper {}
export class SeeTap { observe(payload) {} }
function make() { class LocalFilter { call(payload) { return payload; } } }
`,
    "tests/steps.ts": `class AFilter { call(payload) { return payload; } }
class BFilter { call(payload) { return payload; } }
`,
    "steps.test.ts": `class AFilter { call(payload) { return payload; } }
class BFilter { call(payload) { return payload; } }
`,
  });
  assert.deepEqual(out.found, ["set-filter.ts:3 CUP-I005", "set-filter.ts:3 CUP-I006"]);
  assert.match(out.findings[0]?.message ?? "", /^Tap `SeeTap` shares this file with Filter `SetFilter`\./);
});

test("CUP-I006: the file name is the class name in kebab-case", async () => {
  const out = await lintIn({
    "discount.ts": `export class DiscountFilter { call(payload) { return payload; } }\n`,
    "parse-html-filter.ts": `export class ParseHTMLFilter { call(payload) { return payload; } }\n`,
    "pricing-pipeline.tsx": `import { Pipeline } from "codeupipe";\nexport class PricingPipeline extends Pipeline {}\n`,
  });
  assert.deepEqual(out.found, ["discount.ts:1 CUP-I006"]);
  assert.match(out.findings[0]?.message ?? "", /`DiscountFilter` is in `discount\.ts`\. Put it in `discount-filter\.ts`\./);
});

test("CUP-I007: the class name ends with its role", async () => {
  const out = await lintIn({
    "discount.ts": `export class Discount { call(payload) { return payload; } }\n`,
    "audit.ts": `import type { Tap } from "codeupipe";\nexport class Audit implements Tap { observe() {} }\n`,
    "at-least.ts": `export class AtLeast { test(payload) { return true; } }\n`,
    "print-steps.ts": `import { Hook } from "codeupipe";\nexport class PrintSteps extends Hook {}\n`,
    "pricing.ts": `import { Pipeline } from "codeupipe";\nexport class Pricing extends Pipeline {}\n`,
    "point.ts": `export class Point { call(a, b) {} test() {} observe(options = {}) {} }\n`,
  });
  assert.deepEqual(out.found, ["at-least.ts:1 CUP-I006", "at-least.ts:1 CUP-I007", "audit.ts:2 CUP-I006", "audit.ts:2 CUP-I007",
    "discount.ts:1 CUP-I006", "discount.ts:1 CUP-I007", "pricing.ts:2 CUP-I006", "pricing.ts:2 CUP-I007",
    "print-steps.ts:2 CUP-I006", "print-steps.ts:2 CUP-I007"]);
  assert.match(out.findings[1]?.message ?? "", /^Predicate `AtLeast` does not say what it is\. Name it `AtLeastPredicate`\./);
});

test("the comment markers suppress the invariant findings", async () => {
  const out = await lintIn({
    "discount.ts": `// cup: allow-name\nexport class Discount { call(payload) { return payload; } }\n`,
    "mark-tap.ts": `export class MarkTap {\n  observe(payload) {\n    payload.insert("a", 1); // cup: allow-outside-write\n  }\n}\n`,
  });
  assert.deepEqual(out.found, []);
  assert.equal(out.suppressed, 3);
});

test("a file with a syntax error is CUP-I000", async () => {
  const out = await lintIn({ "broken.ts": `export class {{{\n` });
  assert.deepEqual(out.found.map((line) => line.split(" ")[1]), ["CUP-I000"]);
});
