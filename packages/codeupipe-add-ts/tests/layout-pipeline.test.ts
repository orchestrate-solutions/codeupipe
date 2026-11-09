// LayoutPipeline: `codeupipe add --layout`, run as a user runs it.
import assert from "node:assert/strict";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { project, run } from "./add-in.ts";

const LAYOUT = [
  "lang: typescript",
  "root: src/pricing",
  "components:",
  "  - {kind: filter, name: Discount, description: \"Takes a rate off the price.\"}",
  "  - {kind: predicate, name: AtLeast}",
  "  - {kind: filter, name: MarkBulk}",
  "  - {kind: pipeline, name: Pricing, steps: [Discount, {valve: [AtLeast, MarkBulk]}]}",
  "",
].join("\n");

test("a layout makes each component, then a run keeps them", () => {
  const root = project({ "cup.layout.yaml": LAYOUT });
  const first = run(root, "--layout", "cup.layout.yaml");
  assert.equal(first.code, 0, first.err);
  assert.equal(first.out.trim().split("\n").length, 8);
  const pipeline = readFileSync(join(root, "src/pricing/pricing-pipeline.ts"), "utf8");
  assert.match(pipeline, /this\.addValve\(new AtLeastPredicate\(\), new MarkBulkFilter\(\)\);/);
  const again = run(root, "--layout", "cup.layout.yaml");
  assert.equal(again.code, 0);
  assert.equal(again.out, "");
  assert.match(again.err, /src\/pricing\/pricing-pipeline\.ts exists, kept\n/);
});

test("a kept pipeline whose steps changed is named", () => {
  const root = project({ "cup.layout.yaml": LAYOUT });
  run(root, "--layout", "cup.layout.yaml");
  writeFileSync(join(root, "cup.layout.yaml"), LAYOUT.replace("steps: [Discount,", "steps: [MarkBulk, Discount,"));
  const again = run(root, "--layout", "cup.layout.yaml");
  assert.equal(again.code, 0);
  assert.match(again.err, /pricing-pipeline\.ts exists, kept, and its steps are not those of the layout\./);
  assert.doesNotMatch(again.err, /discount-filter\.ts exists, kept, and/);
});

test("a refused layout writes nothing, and --layout takes nothing else", () => {
  const root = project({ "cup.layout.yaml": LAYOUT.replace("name: MarkBulk}", "name: MarkBulk, steps: []}") });
  const refused = run(root, "--layout", "cup.layout.yaml");
  assert.equal(refused.code, 2);
  assert.match(refused.err, /steps: is only for a pipeline/);
  assert.ok(!existsSync(join(root, "src")));
  assert.equal(run(root, "filter", "--layout", "cup.layout.yaml").code, 2);
  assert.match(run(root, "--layout", "cup.layout.yaml", "--description", "x").err, /--layout takes no/);
  assert.equal(run(root, "--layout").code, 2);
});
