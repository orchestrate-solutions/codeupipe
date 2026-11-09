// WriteFilesFilter: the two files and their directories, or exit 2 with nothing written.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { WriteFilesFilter } from "../src/write-files-filter.ts";
import { project } from "./add-in.ts";

function written(root: string): string[] {
  const out = new WriteFilesFilter().call(new Payload({
    root, component_path: "src/a/x-filter.ts", component_text: "c",
    test_path: "tests/x-filter.test.ts", test_text: "t",
  }));
  return out.get<string[]>("written") ?? [];
}

test("both files are written with their directories, component first", () => {
  const root = project({});
  assert.deepEqual(written(root), ["src/a/x-filter.ts", "tests/x-filter.test.ts"]);
  assert.equal(readFileSync(join(root, "src/a/x-filter.ts"), "utf8"), "c");
  assert.equal(readFileSync(join(root, "tests/x-filter.test.ts"), "utf8"), "t");
});
