import assert from "node:assert/strict";
import { test } from "node:test";

import { lintIn } from "./lint-in.ts";

test("CUP-I009: a comment that allows nothing is a warning", async () => {
  const out = await lintIn({
    "add.ts": `// cup: allow-plain it had a loop before
export function add(a, b) { return a + b; }
export const one = 1; // cup: allow-state-read nothing here reads State
/*
 * cup: allow-plian a kind that does not exist
 */
export const two = 2;
`,
  });
  assert.deepEqual(out.found, ["add.ts:1 CUP-I009", "add.ts:3 CUP-I009", "add.ts:5 CUP-I009"]);
  assert.equal(out.findings[0]?.severity, "warning");
  assert.match(out.findings[0]?.message ?? "", /^The comment `cup: allow-plain` allows nothing\. Remove it/);
  assert.equal(out.exitCode, 0);
  assert.equal((await lintIn({ "add.ts": "// cup: allow-plain no reason\nexport const one = 1;\n" }, { strict: true })).exitCode, 1);
});

test("CUP-I009: a comment that allows a finding is not reported, and text that only names a marker is not a comment", async () => {
  const out = await lintIn({
    "pick.ts": `// cup: allow-plain the entry of the program
export function pick(list) { for (const each of list) { if (each) return each; } return null; }
export function choose(flag) { return flag ? "a" : "b"; } // cup: allow-plain a small helper
/** The marker \`// cup: allow-plain\` allows a finding. */
export const HELP = "say why: // cup: allow-plain <reason>";
export const MORE = \`\${HELP} // cup: allow-plain\`;
`,
  });
  assert.deepEqual(out.found, []);
  assert.equal(out.suppressed, 2);
});

test("CUP-I009: a comment for a rule that is switched off is not reported, and the rule can be switched off", async () => {
  const files = { "pick.ts": "// cup: allow-plain the entry\nexport function pick(flag) { return flag ? 1 : 2; }\n" };
  const off = await lintIn(files, { disable: ["CUP-I008"] });
  assert.deepEqual(off.found, []);
  assert.equal(off.suppressed, 0);
  assert.deepEqual((await lintIn({ "one.ts": "// cup: allow-plain no reason\nexport const one = 1;\n" }, { disable: ["CUP-I009"] })).found, []);
});
