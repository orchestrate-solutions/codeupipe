// WriteFilesFilter: write the two files, and the directories that they need.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";

/**
 * Filter (sync).
 *
 * Input keys: `root`, `component_path`, `component_text`, `test_path`,
 * `test_text`.
 * Output keys: `written` (the two paths, component first). A directory that
 * cannot be made is refused with exit code 2, before a file is written.
 */
export class WriteFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const root: string = payload.get<string>("root", "");
    const files: Array<[string, string]> = [
      [payload.get<string>("component_path", ""), payload.get<string>("component_text", "")],
      [payload.get<string>("test_path", ""), payload.get<string>("test_text", "")],
    ];
    for (const [path] of files) {
      try {
        mkdirSync(dirname(join(root, path)), { recursive: true });
      } catch (error) {
        throw new Refusal(2, `Cannot make the directory of ${path}: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
    for (const [path, text] of files) writeFileSync(join(root, path), text);
    return payload.insert("written", files.map(([path]) => path));
  }
}
