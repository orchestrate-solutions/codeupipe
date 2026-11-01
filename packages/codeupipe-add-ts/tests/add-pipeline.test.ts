// AddPipeline and the command: the two files, the printed paths, and the exit codes (ADD.md).
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { AddPipeline } from "../src/add-pipeline.ts";
import { project, run } from "./add-in.ts";

async function add(root: string, kind: string, name: string, directory = ".", description = ""): Promise<string[]> {
  const out = await new AddPipeline().run(new Payload({
    root, kind, name, directory, description,
  }));
  return out.get<string[]>("written") ?? [];
}

/** The file name of a component: the rule of the linters (CUP-I006), in kebab-case. */
function kebabOf(kind: string, name: string): string {
  const role = kind.slice(0, 1).toUpperCase() + kind.slice(1);
  const type = name.endsWith(role) ? name : name + role;
  return type.replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, "-").toLowerCase();
}

test("the pipeline makes the two files and prints the component first", async () => {
  const root = project({});
  assert.deepEqual(await add(root, "filter", "Discount"), ["discount-filter.ts", "tests/discount-filter.test.ts"]);
  assert.match(readFileSync(join(root, "discount-filter.ts"), "utf8"), /class DiscountFilter implements Filter/);
});

test("the command prints each path it made, and refuses to write it again", async () => {
  const root = project({});
  const first = run(root, "filter", "Discount", "--description", "Takes a rate off the price.");
  assert.equal(first.code, 0, first.err);
  assert.deepEqual(first.out.split("\n").filter((line) => line !== ""),
                   ["discount-filter.ts", "tests/discount-filter.test.ts"]);
  const again = run(root, "filter", "Discount");
  assert.equal(again.code, 1);
  assert.match(again.err, /discount-filter\.ts exists/);
});

test("a kind that is not made with add writes nothing and exits 2", () => {
  const root = project({});
  const done = run(root, "valve", "AtLeast");
  assert.equal(done.code, 2);
  assert.match(done.err, /add_valve\(predicate, filter\)/);
  assert.equal(existsSync(join(root, "at-least-valve.ts")), false);
});

test("the component of each kind builds and does nothing", async () => {
  const names = { filter: "Discount", predicate: "AtLeast", tap: "Audit", hook: "PrintSteps", pipeline: "Pricing" };
  for (const [kind, name] of Object.entries(names)) {
    const root = project({});
    await add(root, kind, name);
    const component = readFileSync(join(root, kebabOf(kind, name) + ".ts"), "utf8");
    assert.match(component, /codeupipe/, kind);
    assert.ok(!/class \w+ \{[^}]*if \(/.test(component), kind);
  }
});
