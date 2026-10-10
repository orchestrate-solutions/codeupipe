import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import type { Filter, Payload } from "codeupipe";

import { fnmatch } from "./fnmatch.ts";

const EXTENSIONS = [".ts", ".tsx", ".mts", ".cts"];
const SKIP_DIRS = new Set([".git", "node_modules", "build", "dist", "coverage"]);

function isSource(path: string): boolean {
  return EXTENSIONS.some((extension) => path.endsWith(extension)) && !/\.d\.[cm]?ts$/.test(path);
}

/**
 * The TypeScript source files under the given paths.
 *
 * Input keys: `paths` (files or directories), optional `exclude` (globs
 * matched against the path of each file).
 * Output keys: `files` (paths), `errors` (appended).
 *
 * Directories are walked. Version control, dependency and build-output
 * directories are not read, and nor are `.d.ts` files.
 */
export class CollectFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const exclude = payload.get<string[]>("exclude") ?? [];
    const errors = [...(payload.get<string[]>("errors") ?? [])];
    const files: string[] = [];

    const take = (path: string) => {
      if (isSource(path) && !exclude.some((pattern) => fnmatch(path, pattern))) files.push(path);
    };
    const walk = (directory: string) => {
      for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
        const path = join(directory, entry.name);
        if (entry.isDirectory()) {
          if (!SKIP_DIRS.has(entry.name)) walk(path);
        } else if (entry.isFile()) {
          take(path);
        }
      }
    };

    for (const root of payload.get<string[]>("paths") ?? []) {
      const stat = statSync(root, { throwIfNoEntry: false });
      if (stat === undefined) errors.push(`${root}: no such file or directory`);
      else if (stat.isDirectory()) walk(root);
      else take(root);
    }
    return payload.insert("files", files).insert("errors", errors);
  }
}
