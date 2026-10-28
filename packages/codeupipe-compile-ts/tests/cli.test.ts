import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { PIPELINE_IMPORT, project } from "./compile-in.ts";

const CLI = join(import.meta.dirname, "../src/cli.ts");
const STEP = `export class SetFilter { call(payload) { return payload.insert("a", 1); } }\n`;
const pipeline = (extra = "") => PIPELINE_IMPORT + `import { SetFilter } from "./set-filter.ts";
export class MainPipeline extends Pipeline { constructor() { super(); this.addFilter(new SetFilter()); ${extra} } }
`;

function run(cwd: string, ...args: string[]) {
  const done = spawnSync(process.execPath, [CLI, ...args], { cwd, encoding: "utf8" });
  return { code: done.status, out: done.stdout, err: done.stderr };
}

test("exit 0: the module is written, and its path is printed", () => {
  const root = project({ "set-filter.ts": STEP, "pipeline.ts": pipeline() });
  const done = run(root, "pipeline.ts:MainPipeline", "--out", "build/main.ts");
  assert.equal(done.code, 0, done.err);
  assert.equal(done.out.trim(), "build/main.ts");
  assert.match(readFileSync(join(root, "build/main.ts"), "utf8"), /export async function run/);
});

test("exit 1: a refusal names the place and the fix, and nothing is written", () => {
  const root = project({ "set-filter.ts": STEP, "pipeline.ts": pipeline("this.useHook(null);") });
  const done = run(root, "pipeline.ts:MainPipeline", "--out", "build/main.ts");
  assert.equal(done.code, 1);
  assert.match(done.err, /^refused: MainPipeline: the pipeline has a Hook\. /);
  assert.equal(existsSync(join(root, "build")), false);
});

test("exit 2: wrong arguments, and a file that is not there", () => {
  const root = project({});
  assert.equal(run(root).code, 2);
  assert.equal(run(root, "pipeline.ts:MainPipeline").code, 2);
  assert.equal(run(root, "pipeline.ts", "--out", "x.ts").code, 2);
  assert.equal(run(root, "nothing.ts:MainPipeline", "--out", "x.ts").code, 2);
});
