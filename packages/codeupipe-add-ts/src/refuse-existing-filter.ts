// RefuseExistingFilter: a file that exists is never written over (ADD.md, exit 1).
import { existsSync } from "node:fs";
import { join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";

/**
 * Filter (sync).
 *
 * Input keys: `root`, `component_path`, `test_path`.
 * Output keys: none. When either file exists, it refuses with exit code 1 and
 * names each file that exists. Both files are checked before one is written,
 * so the command writes both or neither.
 */
export class RefuseExistingFilter implements Filter {
  call(payload: Payload): Payload {
    const root: string = payload.get<string>("root", "");
    const there = [payload.get<string>("component_path", ""), payload.get<string>("test_path", "")]
      .filter((path) => existsSync(join(root, path)));
    if (there.length > 0) throw new Refusal(1, there.map((path) => `${path} exists`).join("\n"));
    return payload;
  }
}
