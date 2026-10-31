// StalePipelinesFilter: a kept pipeline file whose steps are not those of the layout.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { StalePipelinesFilter } from "../src/stale-pipelines-filter.ts";
import { project } from "./add-in.ts";

const LAYOUT = "this.addFilter(new DiscountFilter());\nthis.addTap(new AuditTap());\n";

function stale(onDisk: string): string[] {
  const root = project({ "p.ts": onDisk });
  return new StalePipelinesFilter().call(new Payload({
    root, kept: ["p.ts"], components: [{ kind: "pipeline", component_path: "p.ts", component_text: LAYOUT }],
  })).get<string[]>("stale", []);
}

test("a kept pipeline is stale only when its steps changed", () => {
  assert.deepEqual(stale(LAYOUT), []);
  // Arguments and comments do not count.
  assert.deepEqual(stale("// a note\nthis.addFilter(new DiscountFilter(0.1));\nthis.addTap(new AuditTap(/* log */));\n"), []);
  assert.deepEqual(stale("this.addTap(new AuditTap());\nthis.addFilter(new DiscountFilter());\n"), ["p.ts"]);
  assert.deepEqual(stale("this.addFilter(new DiscountFilter());\n"), ["p.ts"]);
});
