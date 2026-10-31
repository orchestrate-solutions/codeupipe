// PlanFilesFilter: where the two files go, and how the test imports the component.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { PlanFilesFilter } from "../src/plan-files-filter.ts";

function planned(directory: string): [string, string, string] {
  const out = new PlanFilesFilter().call(new Payload({ directory, kebab: "discount-filter" }));
  return [out.get<string>("component_path") ?? "", out.get<string>("test_path") ?? "", out.get<string>("import_path") ?? ""];
}

test("the component goes in the directory and the test in tests/", () => {
  assert.deepEqual(planned("."), ["discount-filter.ts", "tests/discount-filter.test.ts", "../discount-filter.ts"]);
  assert.deepEqual(planned("src/pricing"), ["src/pricing/discount-filter.ts", "tests/discount-filter.test.ts",
                                            "../src/pricing/discount-filter.ts"]);
});

test("a ./ and a trailing / in the directory make no difference", () => {
  assert.deepEqual(planned("./src/"), ["src/discount-filter.ts", "tests/discount-filter.test.ts",
                                       "../src/discount-filter.ts"]);
});
