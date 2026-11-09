// TypeNameFilter: the type name and the file name from the kind and the name (ADD.md, "Names").
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { Refusal } from "../src/add-refusal.ts";
import { TypeNameFilter } from "../src/type-name-filter.ts";

function named(kind: string, name: string): [string, string] {
  const out = new TypeNameFilter().call(new Payload({ kind, name }));
  return [out.get<string>("type_name") ?? "", out.get<string>("kebab") ?? ""];
}

test("the role suffix is added once, and the file name follows the rule of the linters", () => {
  const cases: Array<[string, string, string, string]> = [
    ["filter", "Discount", "DiscountFilter", "discount-filter"],
    ["filter", "DiscountFilter", "DiscountFilter", "discount-filter"],
    ["predicate", "at_least", "AtLeastPredicate", "at-least-predicate"],
    ["tap", "audit-log", "AuditLogTap", "audit-log-tap"],
    ["filter", "HTTPGet", "HTTPGetFilter", "http-get-filter"],
    ["hook", "printSteps", "PrintStepsHook", "print-steps-hook"],
    ["pipeline", "Pricing", "PricingPipeline", "pricing-pipeline"],
  ];
  for (const [kind, name, type, kebab] of cases) assert.deepEqual(named(kind, name), [type, kebab], `${kind} ${name}`);
});

test("a kind or a name that cannot be used is refused with exit 2", () => {
  const refused: Array<[string, string, string]> = [
    ["valve", "AtLeast", "add_valve(predicate, filter)"],
    ["payload", "Order", "runtime"],
    ["state", "Run", "runtime"],
    ["widget", "Thing", "filter, predicate, tap, hook"],
    ["filter", "2Fast", "2Fast"],
    ["filter", "Take Rate", "Take Rate"],
    ["filter", "", "name"],
  ];
  for (const [kind, name, wanted] of refused) {
    assert.throws(() => named(kind, name), (error: unknown) => {
      assert.ok(error instanceof Refusal, `${kind} ${name}: ${error}`);
      assert.equal(error.exitCode, 2, `${kind} ${name}`);
      assert.match(error.message, new RegExp(wanted.replace(/[(),]/g, "\\$&")));
      return true;
    }, `${kind} ${name}`);
  }
});
