// RenderFilesFilter: the text of the two files (ADD.md, "What the component file has").
import assert from "node:assert/strict";
import { test } from "node:test";

import { Payload } from "codeupipe";

import { RenderFilesFilter } from "../src/render-files-filter.ts";
import { COMPONENTS } from "../src/templates.ts";

function rendered(kind: string, description = ""): { component: string; test: string } {
  const out = new RenderFilesFilter().call(new Payload({
    kind, type_name: "XFilter", kebab: "x-filter", import_path: "../x-filter.ts", description,
  }));
  return { component: out.get<string>("component_text") ?? "", test: out.get<string>("test_text") ?? "" };
}

test("each kind gives TypeScript that parses", async () => {
  const typescript = (await import("typescript")).default;
  for (const kind of Object.keys(COMPONENTS).sort()) {
    for (const text of [rendered(kind).component, rendered(kind).test]) {
      const tree = typescript.createSourceFile(`${kind}.ts`, text, typescript.ScriptTarget.ES2022, true);
      assert.equal(((tree as unknown as { parseDiagnostics?: unknown[] }).parseDiagnostics ?? []).length, 0, `${kind}: ${text}`);
    }
  }
});

test("the header has the description, or a TODO with no description", () => {
  assert.match(rendered("filter", "Takes a rate off the price.").component,
               /^\/\/ XFilter: Takes a rate off the price\./);
  assert.match(rendered("filter").component, /^\/\/ XFilter: TODO: say what XFilter does\./);
});

test("a description cannot end its comment line early", () => {
  const component = rendered("filter", "A line.\n// console.log(1)").component;
  assert.ok(!/console\.log/.test(component), component);
  assert.match(component.split("\n")[0] ?? "", /^\/\/ XFilter: A line\./, component);
});

test("the test imports the component and fails on purpose", () => {
  const text = rendered("filter").test;
  assert.match(text, /import \{ XFilter \} from "\.\.\/x-filter\.ts";/);
  assert.match(text, /Write the acceptance case for XFilter\./);
  assert.match(text, /node:test/);
});
