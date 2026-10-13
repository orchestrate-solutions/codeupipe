import assert from "node:assert/strict";
import { test } from "node:test";

import { lintIn } from "./lint-in.ts";

const warnings = (out: Awaited<ReturnType<typeof lintIn>>) =>
  out.findings.filter((finding) => finding.severity === "warning").map((finding) => finding.message.split(" has logic")[0]);

test("CUP-I008: a function with a decision that is not in a primitive is a warning", async () => {
  const out = await lintIn({
    "who-is-due.ts": `export function whoIsDue(entries) { if (entries.length === 0) return "say"; return "model"; }
export const pick = (list) => { for (const each of list) { if (each) return each; } return null; };
export const choose = (flag) => (flag ? "a" : "b");
export async function load(path) { try { return await read(path); } catch { return null; } }
export function plain(a, b) { return a + b; }
export const double = (n) => n * 2;
`,
  });
  assert.deepEqual(out.found, ["who-is-due.ts:1 CUP-I008", "who-is-due.ts:2 CUP-I008", "who-is-due.ts:3 CUP-I008", "who-is-due.ts:4 CUP-I008"]);
  assert.deepEqual(warnings(out), ["Function `whoIsDue`", "Function `pick`", "Function `choose`", "Function `load`"]);
  assert.match(out.findings[0]?.message ?? "", /is not a Filter, a Predicate, a Tap, a Hook or a Pipeline\. Write it as a primitive/);
});

test("CUP-I008: a class that is not a primitive, and code at the top of a file", async () => {
  const out = await lintIn({
    "record-store.ts": `export class RecordStore {
  list() { return this.files.filter((file) => file.endsWith(".jsonl")); }
  read(id) { if (!this.has(id)) throw new Error("none"); return []; }
}
export class Point { constructor(x) { this.x = x; } get double() { return this.x * 2; } }
`,
    "main.ts": `import { run } from "./run.ts";
const args = process.argv.slice(2);
if (args.length === 0) process.exit(2);
for (const arg of args) run(arg);
`,
  });
  assert.deepEqual(out.found, ["main.ts:3 CUP-I008", "record-store.ts:1 CUP-I008"]);
  assert.deepEqual(warnings(out), ["The code at the top of this file", "Class `RecordStore`"]);
});

test("CUP-I008: logic in a primitive is where it must be, and types have no logic", async () => {
  const out = await lintIn({
    "pick-filter.ts": `export class PickFilter { call(payload) { if (payload.has("a")) return payload.insert("b", 1); for (const k of []) {} return payload; } }\n`,
    "is-on-predicate.ts": `export class IsOnPredicate { test(payload) { return payload.get("on") ? true : false; } }\n`,
    "see-tap.ts": `export class SeeTap { observe(payload) { if (payload.has("x")) console.log(1); } }\n`,
    "log-hook.ts": `import { Hook } from "codeupipe";\nexport class LogHook extends Hook { override before(step) { if (step) console.log(step); } }\n`,
    "main-pipeline.ts": `import { Pipeline } from "codeupipe";\nexport class MainPipeline extends Pipeline { constructor() { super(); if (process.env.X) this.observe(); } }\n`,
    "types.ts": `export type Due = "say" | "model";\nexport interface Model { reply(text: string): string }\nexport const LIMIT = 20000;\nexport const NAMES = ["a", "b"];\n`,
  });
  assert.deepEqual(out.found, []);
});

test("a warning does not fail the run, unless the run is strict", async () => {
  const files = { "helper.ts": `export function pick(a) { return a ? 1 : 2; }\n` };
  const soft = await lintIn(files);
  assert.equal(soft.exitCode, 0);
  assert.match(soft.report, /helper\.ts:1:17  CUP-I008 logic-outside-primitive  warning: Function `pick` has logic/);
  assert.match(soft.report, /^No findings\. 1 warning\.$/m);
  const strict = await lintIn(files, { strict: true });
  assert.equal(strict.exitCode, 1);
});

test("a warning and a finding are counted apart", async () => {
  const out = await lintIn({ "discount.ts": `export class Discount { call(payload) { return payload; } }\nexport function pick(a) { return a ? 1 : 2; }\n` });
  assert.equal(out.exitCode, 1);
  assert.match(out.report, /^2 findings\. 1 warning\.$/m);
});

test("cup: allow-plain with a reason suppresses the warning, and test files are not checked", async () => {
  const out = await lintIn({
    "helper.ts": `// cup: allow-plain a pure helper of two Predicates\nexport function pick(a) { return a ? 1 : 2; }\n`,
    "helper.test.ts": `export function pick(a) { return a ? 1 : 2; }\n`,
    "tests/support.ts": `export function pick(a) { return a ? 1 : 2; }\n`,
  });
  assert.deepEqual(out.found, []);
  assert.equal(out.suppressed, 1);
  assert.match(out.report, /^No findings \(1 suppressed\)\.$/m);
});

test("the rule can be switched off", async () => {
  const out = await lintIn({ "helper.ts": `export function pick(a) { return a ? 1 : 2; }\n` }, { disable: ["CUP-I008"] });
  assert.deepEqual(out.found, []);
  assert.match(out.report, /^No findings\.$/m);
});
