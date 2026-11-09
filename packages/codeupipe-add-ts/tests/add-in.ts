// A helper for the tests: a new project directory, and the command run in it.
import { mkdtempSync, realpathSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";

export const CLI = join(import.meta.dirname, "../src/cli.ts");

/** A new empty project directory, with `files` in it. */
export function project(files: Record<string, string> = {}): string {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "cup-add-")));
  for (const [name, text] of Object.entries(files)) {
    const path = join(root, name);
    writeFileSync(path, text);
  }
  return root;
}

export type Ran = { code: number; out: string; err: string };

/** Run the command in `cwd` as a user would. */
export function run(cwd: string, ...args: string[]): Ran {
  const done = spawnSync(process.execPath, [CLI, ...args], { cwd, encoding: "utf8" });
  return { code: done.status ?? 0, out: done.stdout, err: done.stderr };
}
