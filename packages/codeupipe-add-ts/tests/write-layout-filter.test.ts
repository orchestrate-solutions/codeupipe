// WriteLayoutFilter: write each file of the layout that is not there yet (ADD.md, "Files that exist").
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { WriteLayoutFilter } from "../src/write-layout-filter.ts";
import { project } from "./add-in.ts";

test("a file that exists is kept by itself, and the others are written", () => {
  const root = project({ "a.ts": "mine\n" });
  const out = new WriteLayoutFilter().call(new Payload({ root, components: [
    { component_path: "a.ts", component_text: "new\n", test_path: "tests/a.test.ts", test_text: "test\n" },
    { component_path: "src/b.ts", component_text: "b\n", test_path: "tests/b.test.ts", test_text: "bt\n" },
  ] }));
  assert.deepEqual(out.get("kept"), ["a.ts"]);
  assert.deepEqual(out.get("written"), ["tests/a.test.ts", "src/b.ts", "tests/b.test.ts"]);
  assert.equal(readFileSync(join(root, "a.ts"), "utf8"), "mine\n");
  assert.equal(readFileSync(join(root, "src/b.ts"), "utf8"), "b\n");
});
