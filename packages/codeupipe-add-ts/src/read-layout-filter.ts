// ReadLayoutFilter: the layout file, as data (ADD.md, "The YAML reader").
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import { Refusal } from "./add-refusal.ts";

type YamlError = Error & { code?: string; pos?: [number, number]; linePos?: Array<{ line: number }> };
type Yaml = { parse(text: string, options: { uniqueKeys: boolean }): unknown };

/**
 * Filter (sync).
 *
 * Input keys: `root`, `layout_path` (relative to the root).
 * Output keys: `layout` (an object). JSON is YAML, so one reader, the `yaml`
 * package, reads both; it is loaded only here, so phase 1 reads no YAML. A
 * file that cannot be read, a key two times in one mapping, or a layout that
 * is not a mapping is refused with exit code 2.
 */
export class ReadLayoutFilter implements Filter {
  call(payload: Payload): Payload {
    const path: string = payload.get<string>("layout_path", "");
    let text: string;
    try {
      text = readFileSync(join(payload.get<string>("root", ""), path), "utf8");
    } catch (error) {
      throw new Refusal(2, `The layout ${path} cannot be read: ${error instanceof Error ? error.message : String(error)}`);
    }
    let layout: unknown;
    try {
      const yaml = createRequire(import.meta.url)("yaml") as Yaml;
      layout = yaml.parse(text, { uniqueKeys: true });
    } catch (error) {
      const failed = error as YamlError;
      if (failed.code === "MODULE_NOT_FOUND") {
        throw new Refusal(2, `The layout ${path} needs the yaml package: npm install yaml.`);
      }
      if (failed.code === "DUPLICATE_KEY" && failed.pos) {
        throw new Refusal(2, `The layout ${path}, line ${failed.linePos?.[0]?.line ?? "?"} has the key `
          + `${this.keyAt(text, failed.pos[0])} two times in one mapping. Keep one.`);
      }
      throw new Refusal(2, `The layout ${path} cannot be read: ${failed.message.split("\n")[0]}`);
    }
    if (typeof layout !== "object" || layout === null || Array.isArray(layout)) {
      throw new Refusal(2, `The layout ${path} is not a mapping. It starts with keys such as lang: and components:.`);
    }
    return payload.insert("layout", layout);
  }

  /** The key at `at` in `text`: a quoted key, or the word up to the colon. */
  private keyAt(text: string, at: number): string {
    const found = /^"([^"]*)"|^'([^']*)'|^[^:\s,{}]+/.exec(text.slice(at));
    return found ? (found[1] ?? found[2] ?? found[0]) : "?";
  }
}
