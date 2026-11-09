// StalePipelinesFilter: a kept pipeline file whose steps are not those of the layout.
import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import type { Rendered } from "./render-layout-filter.ts";

const CALL = /this\.(addFilter|addValve|addTap|addPipeline|useHook)\(/g;
const TYPE = /\b([A-Z]\w*)\(/g;
const COMMENT = /\/\/[^\n]*|\/\*[\s\S]*?\*\//g;

/**
 * Filter (sync).
 *
 * Input keys: `root`, `components`, `kept`.
 * Output keys: `stale`: the path of each kept pipeline file whose steps are
 * not those that the layout gives. A file that a user filled in is not stale
 * while its steps are the same.
 */
export class StalePipelinesFilter implements Filter {
  call(payload: Payload): Payload {
    const root: string = payload.get<string>("root", "");
    const kept = new Set(payload.get<string[]>("kept", []));
    const stale = payload.get<Rendered[]>("components", [])
      .filter((component) => component.kind === "pipeline" && kept.has(component.component_path))
      .filter((component) => this.steps(readFileSync(join(root, component.component_path), "utf8")) !== this.steps(component.component_text))
      .map((component) => component.component_path);
    return payload.insert("stale", stale);
  }

  /** The method and the types of each call, in order. The arguments and the comments do not count. */
  private steps(text: string): string {
    const code = text.replace(COMMENT, "");
    const found: Array<[string, string[]]> = [];
    for (const call of code.matchAll(CALL)) {
      let depth = 1;
      let end = (call.index ?? 0) + call[0].length;
      const start = end;
      while (depth > 0 && end < code.length) {
        const character = code[end];
        depth += character === "(" ? 1 : character === ")" ? -1 : 0;
        end += 1;
      }
      found.push([call[1] ?? "", [...code.slice(start, end).matchAll(TYPE)].map((type) => type[1] ?? "")]);
    }
    return JSON.stringify(found);
  }
}
