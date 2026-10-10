// The built package in a bundle, as a web app has it: plain, minified, and
// minified with class names kept. The README says what a minifier does to
// labels; this file checks it.
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

import { build } from "esbuild";

const ENTRY = join(import.meta.dirname, "../examples/pricing/browser/entry.ts");
const LABELS = ["DiscountFilter", "MarkBulkFilter", "AuditTap"];

type Result = { output: unknown; labels: string[]; executed: string[] };

async function bundle(options: { minify: boolean; keepNames: boolean }): Promise<{ code: string; result: Result }> {
  const built = await build({
    entryPoints: [ENTRY], bundle: true, write: false, format: "esm", platform: "browser",
    target: "es2022", ...options,
  });
  const code = built.outputFiles[0]?.text ?? "";
  const file = join(mkdtempSync(join(tmpdir(), "cup-bundle-")), "bundle.mjs");
  writeFileSync(file, code);
  await import(pathToFileURL(file).href);
  return { code, result: (globalThis as unknown as { cupResult: Result }).cupResult };
}

test("the bundle for a browser has no import of Node", async () => {
  const { code } = await bundle({ minify: false, keepNames: false });
  assert.doesNotMatch(code, /from\s*"node:|require\(/);
});

test("a plain bundle gives the same result and the same labels", async () => {
  const { result } = await bundle({ minify: false, keepNames: false });
  assert.deepEqual(result.output, { price: 90, qty: 12, bulk: true });
  assert.deepEqual(result.labels, LABELS);
  assert.deepEqual(result.executed, LABELS);
});

test("a minified bundle gives the same result, but the labels are changed", async () => {
  const { result } = await bundle({ minify: true, keepNames: false });
  assert.deepEqual(result.output, { price: 90, qty: 12, bulk: true });
  assert.equal(result.labels.length, 3);
  assert.notDeepEqual(result.labels, LABELS);
});

test("a minified bundle that keeps names has the same labels", async () => {
  const { result } = await bundle({ minify: true, keepNames: true });
  assert.deepEqual(result.output, { price: 90, qty: 12, bulk: true });
  assert.deepEqual(result.labels, LABELS);
});
