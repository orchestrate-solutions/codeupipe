// ReadLayoutFilter: the layout file, as data (ADD.md, "The YAML reader").
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { Refusal } from "../src/add-refusal.ts";
import { ReadLayoutFilter } from "../src/read-layout-filter.ts";
import { project } from "./add-in.ts";

function read(text: string, name = "cup.layout.yaml"): unknown {
  return new ReadLayoutFilter().call(new Payload({ root: project({ [name]: text }), layout_path: name })).get("layout");
}

function refusal(text: string): Refusal {
  try {
    read(text);
  } catch (error) {
    if (error instanceof Refusal) return error;
    throw error;
  }
  throw new Error("not refused");
}

test("YAML and JSON give the same data", () => {
  const yaml = read("lang: typescript\ncomponents:\n  - {kind: filter, name: Discount}\n");
  const json = read('{"lang": "typescript", "components": [{"kind": "filter", "name": "Discount"}]}', "cup.layout.json");
  assert.deepEqual(yaml, json);
});

test("a key two times in one mapping is refused, with the key and the line", () => {
  const refused = refusal("lang: typescript\ncomponents:\n  - kind: filter\n    name: A\n    name: B\n");
  assert.equal(refused.exitCode, 2);
  assert.match(refused.message, /line 5 has the key name two times/);
  assert.match(refusal('{"lang": "a", "lang": "b"}').message, /the key lang two times/);
});

test("a file that is not there, YAML that cannot be read, and a list are refused", () => {
  assert.throws(() => new ReadLayoutFilter().call(new Payload({ root: project(), layout_path: "no.yaml" })),
                /The layout no\.yaml cannot be read/);
  assert.match(refusal("a: [1\n").message, /cannot be read/);
  assert.match(refusal("- lang: typescript\n").message, /is not a mapping/);
});
