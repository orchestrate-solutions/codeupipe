// RenderLayoutFilter: the text of the two files of each component of the layout.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import type { Rendered } from "../src/render-layout-filter.ts";
import { RenderLayoutFilter } from "../src/render-layout-filter.ts";

const PIPELINE = {
  kind: "pipeline", name: "Pricing", description: "Prices an order.", steps: [], hooks: [],
  type_name: "PricingPipeline", kebab: "pricing-pipeline", component_path: "", test_path: "",
  import_path: "../pricing-pipeline.ts",
  calls: [["addFilter", ["DiscountFilter"]], ["addValve", ["AtLeastPredicate", "MarkFilter"]]],
  imports: [["at-least-predicate", "AtLeastPredicate"], ["discount-filter", "DiscountFilter"], ["mark-filter", "MarkFilter"]],
};

test("a pipeline with calls gets its imports and its steps", () => {
  const [rendered] = new RenderLayoutFilter().call(new Payload({ components: [PIPELINE] })).get<Rendered[]>("components", []);
  const text = rendered?.component_text ?? "";
  assert.match(text, /^\/\/ PricingPipeline: Prices an order\./);
  assert.match(text, /import \{ AtLeastPredicate \} from "\.\/at-least-predicate\.ts";/);
  assert.match(text, /this\.addFilter\(new DiscountFilter\(\)\);\n    this\.addValve\(new AtLeastPredicate\(\), new MarkFilter\(\)\);/);
  assert.match(rendered?.test_text ?? "", /Write the acceptance case for PricingPipeline\./);
});

test("a pipeline with no calls is that of phase 1", () => {
  const [rendered] = new RenderLayoutFilter().call(new Payload({ components: [{ ...PIPELINE, calls: [], imports: [] }] }))
    .get<Rendered[]>("components", []);
  assert.match(rendered?.component_text ?? "", /export class PricingPipeline extends Pipeline \{\}/);
});
