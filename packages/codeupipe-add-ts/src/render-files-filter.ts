// RenderFilesFilter: the text of the component file and of the test file.
import type { Filter, Payload } from "codeupipe";

import { COMPONENTS, TEST } from "./templates.ts";

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
 * Input keys: `kind`, `type_name`, `kebab`, `import_path`, `description`.
 * Output keys: `component_text`, `test_text`. With no description, the header
 * says `TODO: say what <type_name> does.`
 */
export class RenderFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const typeName: string = payload.get<string>("type_name", "");
    const description = payload.get<string>("description") || `TODO: say what ${typeName} does.`;
    const values = {
      type_name: typeName,
      description: forComment(description),
      import_path: payload.get<string>("import_path", "") as string,
      kebab: payload.get<string>("kebab", "") as string,
    };
    return payload
      .insert("component_text", fill(COMPONENTS[payload.get<string>("kind", "") as string] ?? "", values))
      .insert("test_text", fill(TEST, values));
  }
}
