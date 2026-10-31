// WriteLayoutFilter: write each file of the layout that is not there yet (ADD.md, "Files that exist").
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";
import type { Rendered } from "./render-layout-filter.ts";

/**
 * Filter (sync).
 *
 * Input keys: `root`, `components` (each with `component_path`,
 * `component_text`, `test_path`, `test_text`).
 * Output keys: `written` and `kept`: the paths, in order, component first. A
 * file that exists is kept, by itself. The directories are made before a file
 * is written; one that cannot be made is refused with exit code 2.
 */
export class WriteLayoutFilter implements Filter {
  call(payload: Payload): Payload {
    const root: string = payload.get<string>("root", "");
    const files = payload.get<Rendered[]>("components", []).flatMap((component): Array<[string, string]> => [
      [component.component_path, component.component_text],
      [component.test_path, component.test_text],
    ]);
    const kept = files.filter(([path]) => existsSync(join(root, path))).map(([path]) => path);
    const fresh = files.filter(([path]) => !kept.includes(path));
    for (const [path] of fresh) {
      try {
        mkdirSync(dirname(join(root, path)), { recursive: true });
      } catch (error) {
        throw new Refusal(2, `Cannot make the directory of ${path}: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
    for (const [path, text] of fresh) writeFileSync(join(root, path), text);
    return payload.insert("written", fresh.map(([path]) => path)).insert("kept", kept);
  }
}
