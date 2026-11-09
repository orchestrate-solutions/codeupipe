// CheckLayoutFilter: the keys of the layout, and the shape of each (ADD.md, "The keys").
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { CheckLayoutFilter } from "../src/check-layout-filter.ts";

function check(layout: unknown): Payload {
  return new CheckLayoutFilter().call(new Payload({ layout }));
}

const FILTER = { kind: "filter", name: "Discount" };

test("a layout gives its directory and each component with every key", () => {
  const out = check({ lang: "typescript", root: "src/pricing", components: [FILTER] });
  assert.equal(out.get("directory"), "src/pricing");
  assert.deepEqual(out.get("components"), [{ ...FILTER, description: "", steps: [], hooks: [] }]);
  assert.equal(check({ lang: "typescript", components: [FILTER] }).get("directory"), ".");
});

test("the lang, the keys and the shapes are checked", () => {
  assert.throws(() => check({ components: [FILTER] }), /has no lang:\. For this command it is lang: typescript/);
  assert.throws(() => check({ lang: "go", components: [FILTER] }), /is for go, and this is codeupipe add for typescript/);
  assert.throws(() => check({ lang: "typescript", component: [FILTER] }), /Unknown key component in the layout/);
  assert.throws(() => check({ lang: "typescript", components: [] }), /components: is a list/);
  assert.throws(() => check({ lang: "typescript", components: [{ name: "X" }] }), /The component X has no kind:/);
  assert.throws(() => check({ lang: "typescript", components: [{ ...FILTER, step: [] }] }), /Unknown key step/);
  assert.throws(() => check({ lang: "typescript", components: [{ ...FILTER, steps: [] }] }),
                /steps: is only for a pipeline, and Discount is a filter/);
  assert.throws(() => check({ lang: "typescript", components: [{ kind: "pipeline", name: "P", steps: [{ valve: ["A"] }] }] }),
                /The step .* of P cannot be read/);
  assert.throws(() => check({ lang: "typescript", components: [{ kind: "pipeline", name: "P", hooks: [1] }] }),
                /The hooks of P are a list of names/);
});
