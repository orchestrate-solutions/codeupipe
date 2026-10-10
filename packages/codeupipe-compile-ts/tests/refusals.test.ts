import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { CompileRefusal, compile } from "../src/index.ts";
import { PIPELINE_IMPORT, project } from "./compile-in.ts";

/** Compile a pipeline of one step, and return the refusal. */
async function refusal(step: string, add: string, extra: Record<string, string> = {}): Promise<CompileRefusal> {
  const root = project({
    "step.ts": step,
    "pipeline.ts": PIPELINE_IMPORT + `import { Step } from "./step.ts";
export class MainPipeline extends Pipeline { constructor() { super(); ${add} } }
`,
    ...extra,
  });
  const outFile = join(root, "compiled.ts");
  try {
    await compile(join(root, "pipeline.ts"), "MainPipeline", { outFile });
  } catch (error) {
    assert.ok(error instanceof CompileRefusal, String(error));
    assert.equal(existsSync(outFile), false, "nothing is written when the pipeline is refused");
    return error;
  }
  throw new Error("the pipeline was not refused");
}

const FILTER = "this.addFilter(new Step());";
const filter = (body: string) => `export class Step { call(payload) { ${body} } }\n`;

const CASES: Array<[string, string, string, RegExp]> = [
  ["a Hook", filter("return payload;"), FILTER + " this.useHook(new Step());", /the pipeline has a Hook/],
  ["timing", filter("return payload;"), FILTER + " this.observe();", /timing or lineage/],
  ["other code in the constructor", filter("return payload;"), FILTER + " console.log(1);", /does not add a step/],
  ["a step that is not made in the call", filter("return payload;"), "const step = new Step(); this.addFilter(step);", /does not add a step/],
  ["an argument that is not a literal", `export class Step { key; constructor(key) { this.key = key; } call(payload) { return payload; } }\n`,
    "this.addFilter(new Step(process.env.KEY));", /is not a literal/],
  ["a setting that the constructor computes", `export class Step { key; constructor(key) { this.key = key + "!"; } call(payload) { return payload; } }\n`,
    `this.addFilter(new Step("a"));`, /computes the setting `key`/],
  ["a write to this", `export class Step { count = 0; call(payload) { this.count += 1; return payload; } }\n`, FILTER, /assigns to `this\.count`/],
  ["a helper method", `export class Step { help() { return 1; } call(payload) { return payload.insert("a", this.help()); } }\n`, FILTER,
    /`this\.help`, which is not a property/],
  ["a class that extends another", `class Base {}\nexport class Step extends Base { call(payload) { return payload; } }\n`, FILTER, /extends another class/],
  ["a return of another Payload", `import { Payload } from "codeupipe";\nexport class Step { call(payload) { return new Payload({}); } }\n`, FILTER,
    /returns something that is not the Payload/],
  ["no return", filter(`payload.insert("a", 1);`), FILTER, /does not return the Payload/],
  ["copy", filter(`const mine = payload.copy(); return payload;`), FILTER, /`payload\.copy` in a form that has no plain code/],
  ["the trace id", filter(`payload.insert("t", payload.traceId); return payload;`), FILTER, /uses `payload\.traceId`/],
  ["the Payload under another name", filter(`const other = payload; return payload;`), FILTER, /gives it another name/],
  ["the Payload given to other code", filter(`console.log(payload); return payload;`), FILTER, /gives the Payload to other code/],
  ["a merge of a Payload from elsewhere", filter(`return payload.merge(globalThis.other);`), FILTER, /merges a Payload that it did not make/],
  ["a name beside the class", `const RATE = 0.1;\nexport class Step { call(payload) { return payload.insert("r", RATE); } }\n`, FILTER,
    /Move `RATE` to its own file and import it/],
  ["a value from codeupipe", `import { State } from "codeupipe";\nexport class Step { call(payload) { return payload.insert("s", new State()); } }\n`, FILTER,
    /uses `State` from codeupipe/],
  ["a name that starts with cup_", filter(`const cup_x = 1; return payload;`), FILTER, /starts with cup_/],
  ["a Tap that writes", `export class Step { observe(payload) { payload.insert("a", 1); } }\n`, "this.addTap(new Step());", /observe writes to the Payload/],
  ["a Predicate that writes", `export class Step { test(payload) { payload.remove("a"); return true; } call(payload) { return payload; } }\n`,
    "this.addValve(new Step(), new Step());", /test writes to the Payload/],
  ["an async Predicate", `export class Step { async test(payload) { return true; } call(payload) { return payload; } }\n`,
    "this.addValve(new Step(), new Step());", /test is async/],
  ["a class with no call", `export class Step { observe(payload) {} }\n`, FILTER, /has no call\(payload\) method/],
];

for (const [name, step, add, message] of CASES) {
  test(`refused: ${name}`, async () => {
    const error = await refusal(step, add);
    assert.match(error.message, message);
    assert.ok(error.hint.length > 0);
  });
}

test("refused: a step from a package", async () => {
  const root = project({
    "pipeline.ts": PIPELINE_IMPORT + `import { Step } from "some-package";
export class MainPipeline extends Pipeline { constructor() { super(); this.addFilter(new Step()); } }
`,
  });
  await assert.rejects(compile(join(root, "pipeline.ts"), "MainPipeline"), /comes from the package "some-package"/);
});

test("refused: a class that is not a Pipeline, and a pipeline that is nested in itself", async () => {
  const root = project({
    "pipeline.ts": PIPELINE_IMPORT + `export class Plain {}
export class LoopPipeline extends Pipeline { constructor() { super(); this.addPipeline(new LoopPipeline()); } }
`,
  });
  await assert.rejects(compile(join(root, "pipeline.ts"), "Plain"), /does not extend Pipeline/);
  await assert.rejects(compile(join(root, "pipeline.ts"), "LoopPipeline"), /nested in itself/);
  await assert.rejects(compile(join(root, "pipeline.ts"), "Missing"), /`Missing` is not a class/);
});
