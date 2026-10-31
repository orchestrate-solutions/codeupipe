// PlanFilesFilter: where the component file and the test file go (ADD.md, "The files").
import type { Filter, Payload } from "codeupipe";

/**
 * Filter (sync).
 *
 * Input keys: `directory` (relative to the root) and `kebab`.
 * Output keys: `component_path` and `test_path` (relative to the root, with
 * `/`), and `import_path`: the path that a test in `tests/` imports, from its
 * own place, so `../` for each step up to the root and then the component.
 */
export class PlanFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const kebab: string = payload.get<string>("kebab", "");
    const directory = payload.get<string>("directory") || ".";
    const parts = directory.split("/").filter((part) => part !== "" && part !== ".");
    const component = [...parts, `${kebab}.ts`].join("/");
    // The test is in `tests/`, so it goes up one step to the root; the path
    // then goes down through the directory of the component.
    const down = [...parts, `${kebab}.ts`];
    const route = ["..", ...down];
    return payload
      .insert("component_path", component)
      .insert("test_path", `tests/${kebab}.test.ts`)
      .insert("import_path", route.join("/"));
  }
}
