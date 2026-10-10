import assert from "node:assert/strict";
import { join } from "node:path";
import { test } from "node:test";

import ts from "typescript";

import { compile } from "../src/index.ts";
import { PIPELINE_IMPORT, compileIn, project } from "./compile-in.ts";

const PRICING = join(import.meta.dirname, "../../codeupipe-ts/examples/pricing/pricing-pipeline.ts");

test("the pricing example compiles, and the code has no import", async () => {
  const code = await compile(PRICING, "PricingPipeline");
  assert.doesNotMatch(code, /^import /m);
  assert.doesNotMatch(code, /codeupipe"/);
  assert.match(code, /export async function run\(/);
});

test("the compiled pricing example gives the same output as the pipeline", async () => {
  const { PricingPipeline } = await import(PRICING);
  const { Payload } = await import("../../codeupipe-ts/src/index.ts");
  const file = join(project({}), "pricing.ts");
  await compile(PRICING, "PricingPipeline", { outFile: file });
  const compiled: { run(input: Record<string, unknown>): Promise<Record<string, unknown>> } = await import(file);
  for (const input of [{ price: 100.0, qty: 12 }, { price: 19.99, qty: 2 }, {}, { qty: 10 }]) {
    const given = structuredClone(input);
    const dynamic = (await new PricingPipeline().run(new Payload(input))).toDict();
    assert.deepEqual(await compiled.run(given), dynamic);
    assert.deepEqual(given, input); // the caller's input is not changed
  }
});

test("the compiled code passes a strict type check", async () => {
  const file = join(project({}), "pricing.ts");
  await compile(PRICING, "PricingPipeline", { outFile: file });
  const program = ts.createProgram([file], {
    strict: true, noEmit: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.NodeNext,
    moduleResolution: ts.ModuleResolutionKind.NodeNext, lib: ["lib.es2022.d.ts"], types: [],
  });
  const problems = ts.getPreEmitDiagnostics(program).map((d) => ts.flattenDiagnosticMessageText(d.messageText, " "));
  assert.deepEqual(problems, []);
});

test("each operation of the Payload has a plain form", async () => {
  const compiled = await compileIn({
    "ops-filter.ts": `import { Payload } from "codeupipe";
export class OpsFilter {
  readonly extra: Record<string, unknown>;
  constructor(extra: Record<string, unknown>) { this.extra = extra; }
  call(payload: Payload): Payload {
    payload.insert("had", payload.has("a")).remove("a");
    payload.merge(new Payload(this.extra));
    payload.insert("copy", payload.toDict());
    payload.insert("missing", payload.get("zz"));
    return payload.insert("n", payload.get<number>("n", 0) + 1).insert("last", true);
  }
}
`,
    "pipeline.ts": PIPELINE_IMPORT + `import { OpsFilter } from "./ops-filter.ts";
export class MainPipeline extends Pipeline {
  constructor() { super(); this.addFilter(new OpsFilter({ b: 2, n: 5 })); }
}
`,
  });
  assert.deepEqual(await compiled.run({ a: 1 }), { had: true, b: 2, n: 6, copy: { had: true, b: 2, n: 5 }, missing: null, last: true });
});

test("a Valve, a Tap that fails, a second use of a class, and a nested pipeline", async () => {
  const compiled = await compileIn({
    "add-filter.ts": `export class AddFilter {
  by: number;
  constructor(by = 1) { this.by = by; }
  call(payload) { return payload.insert("n", payload.get("n", 0) + this.by); }
}
`,
    "is-on-predicate.ts": `export class IsOnPredicate { test(payload) { return payload.get("on") === true; } }\n`,
    "fail-tap.ts": `export class FailTap { observe(payload) { throw new Error("sink is down"); } }\n`,
    "pipeline.ts": PIPELINE_IMPORT + `import { AddFilter } from "./add-filter.ts";
import { FailTap } from "./fail-tap.ts";
import { IsOnPredicate } from "./is-on-predicate.ts";
class InnerPipeline extends Pipeline {
  constructor() { super(); this.addFilter(new AddFilter(10)); this.addTap(new FailTap()); }
}
export class MainPipeline extends Pipeline {
  constructor() {
    super();
    this.addFilter(new AddFilter());
    this.addValve(new IsOnPredicate(), new AddFilter(100));
    this.addPipeline(new InnerPipeline());
  }
}
`,
  });
  assert.deepEqual(await compiled.run({ on: true }), { on: true, n: 111 });
  assert.deepEqual(await compiled.run({ on: false }), { on: false, n: 11 });
  assert.match(compiled.code, /cup_01_add_filter\(data\);\n  if \(cup_02_when_is_on_predicate\(data\)\) cup_02_add_filter\(data\);\n  cup_03_add_filter\(data\);/);
});

test("an async step is awaited, and a Filter failure is the same error", async () => {
  const compiled = await compileIn({
    "later-filter.ts": `export class LaterFilter {
  async call(payload) { await Promise.resolve(); return payload.insert("later", true); }
}
`,
    "check-filter.ts": `export class CheckFilter {
  call(payload) { if (payload.has("bad")) throw new RangeError("bad input"); return payload; }
}
`,
    "pipeline.ts": PIPELINE_IMPORT + `import { CheckFilter } from "./check-filter.ts";
import { LaterFilter } from "./later-filter.ts";
export class MainPipeline extends Pipeline {
  constructor() { super(); this.addFilter(new LaterFilter()); this.addFilter(new CheckFilter()); }
}
`,
  });
  assert.deepEqual(await compiled.run({}), { later: true });
  assert.match(compiled.code, /await cup_01_later_filter\(data\);/);
  await assert.rejects(compiled.run({ bad: 1 }), { name: "RangeError", message: "bad input" });
});

test("an import of a step file is kept, relative to the compiled file", async () => {
  const compiled = await compileIn({
    "rates.ts": `export const RATES: Record<string, number> = { gold: 0.2 };\nexport function round(value: number): number { return Math.round(value * 100) / 100; }\n`,
    "rate-filter.ts": `import type { Payload } from "codeupipe";
import { RATES, round as roundMoney } from "./rates.ts";
export class RateFilter {
  call(payload: Payload): Payload {
    const rate = RATES[payload.get("tier", "")] ?? 0;
    return payload.insert("price", roundMoney(payload.get("price", 0) * (1 - rate)));
  }
}
`,
    "pipeline.ts": PIPELINE_IMPORT + `import { RateFilter } from "./rate-filter.ts";
export class MainPipeline extends Pipeline { constructor() { super(); this.addFilter(new RateFilter()); } }
`,
  });
  assert.match(compiled.code, /^import \{ RATES \} from "\.\/rates\.ts";\nimport \{ round as roundMoney \} from "\.\/rates\.ts";$/m);
  assert.deepEqual(await compiled.run({ tier: "gold", price: 10 }), { tier: "gold", price: 8 });
});
