// RefuseExistingFilter: a file that exists stops the run, and names each file (ADD.md, exit 1).
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { Refusal } from "../src/add-refusal.ts";
import { RefuseExistingFilter } from "../src/refuse-existing-filter.ts";
import { project } from "./add-in.ts";

function check(root: string): void {
  new RefuseExistingFilter().call(new Payload({
    root, component_path: "discount-filter.ts", test_path: "tests/discount-filter.test.ts",
  }));
}

test("no file there goes on", () => {
  check(project({}));
});

test("each file that exists is named, with exit 1", () => {
  const root = project({});
  mkdirSync(join(root, "tests"), { recursive: true });
  writeFileSync(join(root, "discount-filter.ts"), "");
  writeFileSync(join(root, "tests/discount-filter.test.ts"), "");
  assert.throws(() => check(root), (error: unknown) => {
    assert.ok(error instanceof Refusal);
    assert.equal(error.exitCode, 1);
    assert.equal(error.message, "discount-filter.ts exists\ntests/discount-filter.test.ts exists");
    return true;
  });
});
