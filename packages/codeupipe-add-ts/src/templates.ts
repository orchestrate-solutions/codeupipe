/**
 * The text of each file that `codeupipe add` makes, for each kind
 * (conformance/ADD.md, "What the component file has").
 *
 * `{type_name}`, `{description}`, `{import_path}` and `{kebab}` are filled in
 * by RenderFilesFilter. Each component does nothing; the test fails on purpose.
 */
export const COMPONENTS: Record<string, string> = {
  filter: [
    "// {type_name}: {description}",
    'import type { Filter, Payload } from "codeupipe";',
    "",
    "export class {type_name} implements Filter {",
    "  call(payload: Payload): Payload {",
    "    return payload;",
    "  }",
    "}",
    "",
  ].join("\n"),
  predicate: [
    "// {type_name}: {description}",
    'import type { Payload, Predicate } from "codeupipe";',
    "",
    "export class {type_name} implements Predicate {",
    "  test(_payload: Payload): boolean {",
    "    return false;",
    "  }",
    "}",
    "",
  ].join("\n"),
  tap: [
    "// {type_name}: {description}",
    'import type { Payload, Tap } from "codeupipe";',
    "",
    "export class {type_name} implements Tap {",
    "  observe(_payload: Payload): void {}",
    "}",
    "",
  ].join("\n"),
  hook: [
    "// {type_name}: {description}",
    'import { Hook } from "codeupipe";',
    "",
    "export class {type_name} extends Hook {}",
    "",
  ].join("\n"),
  pipeline: [
    "// {type_name}: {description}",
    'import { Pipeline } from "codeupipe";',
    "",
    "export class {type_name} extends Pipeline {}",
    "",
  ].join("\n"),
};

/**
 * The component file of a pipeline of a layout, with its steps (ADD.md, "The
 * steps"). `{imports}` and `{calls}` are lines that RenderFilesFilter makes.
 */
export const PIPELINE_STEPS = [
  "// {type_name}: {description}",
  'import { Pipeline } from "codeupipe";',
  "",
  "{imports}",
  "",
  "export class {type_name} extends Pipeline {",
  "  constructor() {",
  "    super();",
  "{calls}",
  "  }",
  "}",
  "",
].join("\n");

/** The test file: one test that makes the component and fails with the known message. */
export const TEST = [
  "// The acceptance case of {type_name}.",
  'import { test } from "node:test";',
  'import { {type_name} } from "{import_path}";',
  "",
  'test("{type_name} does what it must", () => {',
  "  void new {type_name}();",
  '  throw new Error("Write the acceptance case for {type_name}.");',
  "});",
  "",
].join("\n");
