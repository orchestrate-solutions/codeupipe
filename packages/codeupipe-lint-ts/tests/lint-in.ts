// A helper for the tests: write source text to a new directory and lint it.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";

import { lintPaths } from "../src/index.ts";
import type { Finding } from "../src/index.ts";

export type Linted = { found: string[]; findings: Finding[]; suppressed: number; report: string; exitCode: number };

/** `found` holds one string for each finding: `file:line rule`. */
export async function lintIn(files: Record<string, string>,
                             options: { exclude?: string[]; disable?: string[]; strict?: boolean } = {}): Promise<Linted> {
  const root = mkdtempSync(join(tmpdir(), "cup-lint-"));
  for (const [name, text] of Object.entries(files)) {
    mkdirSync(dirname(join(root, name)), { recursive: true });
    writeFileSync(join(root, name), text);
  }
  const out = await lintPaths([root], options);
  const findings = out.get<Finding[]>("findings") ?? [];
  return {
    findings,
    found: findings.map((f) => `${relative(root, f.path)}:${f.line} ${f.rule}`),
    suppressed: (out.get<Finding[]>("suppressed") ?? []).length,
    report: out.get<string>("report") ?? "",
    exitCode: out.get<number>("exitCode") ?? -1,
  };
}
