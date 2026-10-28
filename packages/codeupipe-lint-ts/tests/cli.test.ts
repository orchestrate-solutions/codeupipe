import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { lintIn } from "./lint-in.ts";

const CLI = join(import.meta.dirname, "../src/cli.ts");
const BAD = `export class Discount { call(payload) { return payload; } }\n`;

function project(files: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "cup-lint-cli-"));
  for (const [name, text] of Object.entries(files)) writeFileSync(join(root, name), text);
  return root;
}

function run(cwd: string, ...args: string[]) {
  const done = spawnSync(process.execPath, [CLI, ...args], { cwd, encoding: "utf8" });
  return { code: done.status, out: done.stdout, err: done.stderr };
}

test("exit 0 with no findings, exit 1 with findings, one line for each", () => {
  const root = project({ "discount.ts": BAD, "set-filter.ts": `export class SetFilter { call(payload) { return payload; } }\n` });
  const clean = run(root, "set-filter.ts");
  assert.equal(clean.code, 0);
  assert.equal(clean.out.trim(), "No findings.");
  const bad = run(root, ".");
  assert.equal(bad.code, 1);
  assert.match(bad.out, /^discount\.ts:1:14  CUP-I006 primitive-file-name  /m);
  assert.match(bad.out, /^2 findings\.$/m);
});

test("exit 2 for a path that is not there, and for a rule that is not known", () => {
  const root = project({});
  assert.equal(run(root, "nothing-here").code, 2);
  const unknown = run(root, "--disable", "CUP-X999", ".");
  assert.equal(unknown.code, 2);
  assert.match(unknown.err, /no such rule: CUP-X999/);
  assert.equal(run(root).code, 2);
});

test("--rules lists the rule ids", () => {
  const listed = run(project({}), "--rules");
  assert.equal(listed.code, 0);
  assert.match(listed.out, /^CUP-A001  lambda-step$/m);
  assert.match(listed.out, /^CUP-I007  primitive-role-suffix$/m);
});

test("--exclude and --disable", () => {
  const root = project({ "discount.ts": BAD });
  assert.equal(run(root, "--exclude", "*/discount.ts", "--exclude", "discount.ts", ".").code, 0);
  assert.equal(run(root, "--disable", "CUP-I006", "--disable", "CUP-I007", ".").code, 0);
  assert.equal(run(root, "--disable", "CUP-I006", ".").code, 1);
});

test("with no paths, they come from cup.config.json", () => {
  const root = project({
    "discount.ts": BAD,
    "cup.config.json": JSON.stringify({ lint: { paths: ["."], disable: ["CUP-I006", "CUP-I007"] } }),
  });
  assert.equal(run(root).code, 0);
  assert.equal(run(root, "discount.ts").code, 1);
  writeFileSync(join(root, "cup.config.json"), JSON.stringify({ lint: { path: ["."] } }));
  const wrong = run(root);
  assert.equal(wrong.code, 2);
  assert.match(wrong.err, /unknown key 'path'/);
});

test("node_modules and dist are not read", async () => {
  const out = await lintIn({ "node_modules/x/discount.ts": BAD, "dist/discount.ts": BAD, "types.d.ts": BAD });
  assert.deepEqual(out.found, []);
});

test("the linter is clean on the TypeScript code of this repository", () => {
  const here = join(import.meta.dirname, "..");
  const done = run(here, "src", "../codeupipe-ts/src", "../codeupipe-ts/examples", "../codeupipe-compile-ts/src",
    "../../conformance/runners/typescript");
  // The plain logic of this repository is reported as warnings. A warning does not fail the run.
  assert.match(done.out, /^No findings[ .]/m);
  assert.equal(done.code, 0);
});
