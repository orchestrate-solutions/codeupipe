import assert from "node:assert/strict";
import { test } from "node:test";

import { lintIn } from "./lint-in.ts";

const HEAD = `import { Pipeline } from "codeupipe";
class AddFilter { call(payload) { return payload; } }
class IsOnPredicate { test(payload) { return true; } }
const pipeline = new Pipeline();
`;

test("named classes at module level are clean", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
pipeline.addFilter(new AddFilter());
pipeline.addValve(new IsOnPredicate(), new AddFilter());
const kept = new AddFilter();
pipeline.addFilter(kept);
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, []);
  assert.equal(out.exitCode, 0);
  assert.match(out.report, /^No findings\.$/);
});

test("CUP-A001: an arrow function or a function expression as a step", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
pipeline.addFilter((payload) => payload);
pipeline.addTap(function (payload) {});
const later = (payload) => payload;
pipeline.addFilter(later);
pipeline.addValve((payload) => true, new AddFilter());
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:6 CUP-A001", "build.ts:7 CUP-A001", "build.ts:9 CUP-A001", "build.ts:10 CUP-A001"]);
  assert.match(out.findings[0]?.message ?? "", /^Filter is a function\./);
  assert.match(out.findings[2]?.message ?? "", /^Filter `later` is a function\./);
  assert.match(out.findings[3]?.message ?? "", /^Valve predicate is a function\./);
  assert.equal(out.exitCode, 1);
});

test("CUP-A002: a named function as a Filter or a Tap", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
function normalize(payload) { return payload; }
pipeline.addFilter(normalize);
pipeline.addTap(normalize);
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:7 CUP-A002", "build.ts:8 CUP-A002"]);
});

test("CUP-A003: a class that is declared in a function, or that has no name", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
function make() {
  class LocalFilter { call(payload) { return payload; } }
  pipeline.addFilter(new LocalFilter());
  const kept = new LocalFilter();
  pipeline.addFilter(kept);
}
pipeline.addFilter(new (class { call(payload) { return payload; } })());
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:8 CUP-A003", "build.ts:10 CUP-A003", "build.ts:12 CUP-A003"]);
});

test("CUP-A005: a plain Pipeline as a step", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
class InnerPipeline extends Pipeline {}
pipeline.addPipeline(new Pipeline());
const inner = new Pipeline();
pipeline.addPipeline(inner);
pipeline.addPipeline(new InnerPipeline());
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:7 CUP-A005", "build.ts:9 CUP-A005"]);
});

test("CUP-A008: a named function as a Valve predicate", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
function isOn(payload) { return true; }
pipeline.addValve(isOn, new AddFilter());
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:7 CUP-A008"]);
});

test("CUP-A009: an object literal as a step", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
pipeline.addFilter({ call(payload) { return payload; } });
const tap = { observe(payload) {} };
pipeline.addTap(tap);
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:6 CUP-A009", "build.ts:8 CUP-A009"]);
});

test("a name that the file does not bind, and a let, are not flagged", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
import { imported } from "./other.ts";
let changed = (payload) => payload;
changed = new AddFilter();
pipeline.addFilter(imported);
pipeline.addFilter(changed);
function use(parameter) { pipeline.addFilter(parameter); }
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, []);
});

test("this.addFilter in a pipeline class is checked too", async () => {
  const out = await lintIn({ "pricing-pipeline.ts": `import { Pipeline } from "codeupipe";
export class PricingPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter((payload) => payload);
  }
}
` });
  assert.deepEqual(out.found, ["pricing-pipeline.ts:5 CUP-A001"]);
});

test("cup: allow-anonymous suppresses a finding on its line, the line above, or the line of the call", async () => {
  const out = await lintIn({ "build.ts": HEAD + `
pipeline.addFilter((payload) => payload); // cup: allow-anonymous a test of the refusal
// cup: allow-anonymous
pipeline.addFilter((payload) => payload);
pipeline.addValve( // cup: allow-anonymous
  (payload) => true,
  new AddFilter());
pipeline.addFilter((payload) => payload);
` }, { disable: ["CUP-I005", "CUP-I006"] });
  assert.deepEqual(out.found, ["build.ts:12 CUP-A001"]);
  assert.equal(out.suppressed, 3);
  assert.match(out.report, /1 finding \(3 suppressed\)\.$/);
});
