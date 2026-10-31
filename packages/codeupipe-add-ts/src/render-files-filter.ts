// RenderFilesFilter: the text of the component file and of the test file.
import type { Filter, Payload } from "codeupipe";

import { COMPONENTS, PIPELINE_STEPS, TEST } from "./templates.ts";

/** A `//` line cannot be ended early by the text: each `//` inside it becomes a
 * single `/`, and each line break a space. */
function forComment(text: string): string {
  return text.replace(/\/\/[^\n]*/g, "/").replace(/[\r\n]+/g, " ");
}

/** Fill `{type_name}`, `{description}`, `{import_path}` and `{kebab}` in `text`. `{{` is one brace. */
// cup: allow-plain a pure fill of the templates: the text has no logic of the command.
function fill(text: string, values: Record<string, string>): string {
  return text.replace(/\{\{|\{(\w+)\}/g, (whole, key?: string) => (key === undefined ? "{" : values[key] ?? whole));
}

/**
 * Filter (sync).
 *
 * Input keys: `kind`, `type_name`, `kebab`, `import_path`, `description`;
 * for a pipeline of a layout, `calls` (`[method, [type names]]`) and
 * `imports` (`[kebab, type name]`).
 * Output keys: `component_text`, `test_text`. With no description, the header
 * says `TODO: say what <type_name> does.` A pipeline with calls gets its steps.
 */
export class RenderFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const typeName: string = payload.get<string>("type_name", "");
    const description = payload.get<string>("description") || `TODO: say what ${typeName} does.`;
    const calls = payload.get<Array<[string, string[]]>>("calls", []);
    const imports = payload.get<Array<[string, string]>>("imports", []);
    const values = {
      type_name: typeName,
      description: forComment(description),
      import_path: payload.get<string>("import_path", "") as string,
      kebab: payload.get<string>("kebab", "") as string,
      imports: imports.map(([kebab, type]) => `import { ${type} } from "./${kebab}.ts";`).join("\n"),
      calls: calls.map(([method, types]) => `    this.${method}(${types.map((type) => `new ${type}()`).join(", ")});`)
        .join("\n"),
    };
    const template = calls.length > 0 ? PIPELINE_STEPS : COMPONENTS[payload.get<string>("kind", "") as string] ?? "";
    return payload
      .insert("component_text", fill(template, values))
      .insert("test_text", fill(TEST, values));
  }
}
