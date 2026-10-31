// ResolveStepsFilter: the calls and the imports of each pipeline of the layout (ADD.md, "The steps").
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import type { Step } from "../src/check-layout-filter.ts";
import type { Resolved } from "../src/resolve-steps-filter.ts";
import { ResolveStepsFilter } from "../src/resolve-steps-filter.ts";

const ROLE: Record<string, string> = { filter: "Filter", predicate: "Predicate", tap: "Tap", hook: "Hook", pipeline: "Pipeline" };

function component(kind: string, name: string, steps: Step[] = [], hooks: string[] = []) {
  const typeName = name + ROLE[kind];
  return { kind, name, description: "", steps, hooks, type_name: typeName, kebab: name.toLowerCase() + "-" + kind,
           component_path: "", test_path: "", import_path: "" };
}

function resolve(...components: ReturnType<typeof component>[]): Resolved[] {
  return new ResolveStepsFilter().call(new Payload({ components })).get<Resolved[]>("components", []);
}

const PARTS = [component("filter", "Discount"), component("predicate", "AtLeast"), component("filter", "Mark"),
               component("tap", "Audit"), component("hook", "Print")];

test("each kind of step gives its call, and the hooks come last", () => {
  const pricing = resolve(...PARTS, component("pipeline", "Pricing",
    ["Discount", { valve: ["AtLeast", "MarkFilter"] }, "Audit"], ["Print"])).at(-1);
  assert.deepEqual(pricing?.calls, [["addFilter", ["DiscountFilter"]], ["addValve", ["AtLeastPredicate", "MarkFilter"]],
                                     ["addTap", ["AuditTap"]], ["useHook", ["PrintHook"]]]);
  assert.deepEqual(pricing?.imports.map(([kebab]) => kebab),
                   ["atleast-predicate", "audit-tap", "discount-filter", "mark-filter", "print-hook"]);
});

test("a step of the wrong kind, or not in the layout, is refused", () => {
  const pipeline = (steps: Step[], hooks: string[] = []) => () => resolve(...PARTS, component("pipeline", "P", steps, hooks));
  assert.throws(pipeline(["Tax"]), /Tax, a step of P, is not a component of the layout/);
  assert.throws(pipeline(["AtLeast"]), /A predicate is not a step: put it in a valve: \[AtLeast, Filter\]/);
  assert.throws(pipeline(["Print"]), /A hook is not a step: put it in hooks: of P/);
  assert.throws(pipeline([{ valve: ["Discount", "AtLeast"] }]), /a valve is \[Predicate, Filter\], and Discount is a filter/);
  assert.throws(pipeline([], ["Discount"]), /Discount in the hooks of P is a filter, not a hook/);
});

test("a pipeline that has itself as a step is refused", () => {
  assert.throws(() => resolve(component("pipeline", "Outer", ["Inner"]), component("pipeline", "Inner", ["Outer"])),
                /A pipeline has itself as a step: OuterPipeline -> InnerPipeline -> OuterPipeline/);
});
