// NameComponentsFilter: the type name and the paths of each component, as in phase 1.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { NameComponentsFilter } from "../src/name-components-filter.ts";

const BASE = { description: "", steps: [], hooks: [] };

test("each component gets the names and the paths of phase 1", () => {
  const out = new NameComponentsFilter().call(new Payload({
    directory: "src/pricing", components: [{ ...BASE, kind: "filter", name: "mark_bulk" }],
  }));
  assert.deepEqual(out.get("components"), [{
    ...BASE, kind: "filter", name: "mark_bulk", type_name: "MarkBulkFilter", kebab: "mark-bulk-filter",
    component_path: "src/pricing/mark-bulk-filter.ts", test_path: "tests/mark-bulk-filter.test.ts",
    import_path: "../src/pricing/mark-bulk-filter.ts",
  }]);
});

test("two components with one type name are refused", () => {
  assert.throws(() => new NameComponentsFilter().call(new Payload({
    directory: ".", components: [{ ...BASE, kind: "filter", name: "Discount" }, { ...BASE, kind: "filter", name: "DiscountFilter" }],
  })), /Two components are DiscountFilter: Discount and DiscountFilter/);
});
