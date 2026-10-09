/**
 * tsc adapter for the step-identity build step (stamp.ts).
 *
 * tsc has no plugin system, so this stamps its output after the build:
 *
 *     tsc && bun run identity/stamp_dist.ts dist
 *
 * Each emitted .js file is labelled by its ORIGINAL source (read from the
 * source map tsc writes), so compiled code reports the same identities as
 * the source did under vitest or Bun.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { labelFor, stampSource } from "./stamp.js";

export function sourceOf(jsFile: string): string {
  const map = `${jsFile}.map`;
  if (!fs.existsSync(map)) return jsFile;
  const { sources, sourceRoot } = JSON.parse(fs.readFileSync(map, "utf8")) as { sources: string[]; sourceRoot?: string };
  const first = sources[0];
  if (!first) return jsFile;
  return path.resolve(path.dirname(jsFile), sourceRoot ?? "", first);
}

export function stampDist(dir: string): number {
  let stamped = 0;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      stamped += stampDist(full);
    } else if (/\.[cm]?js$/.test(entry.name)) {
      const code = fs.readFileSync(full, "utf8");
      const out = stampSource(code, full, labelFor(sourceOf(full)));
      if (out !== code) {
        fs.writeFileSync(full, out);
        stamped += 1;
      }
    }
  }
  return stamped;
}

const target = process.argv[2];
if (target && import.meta.url === `file://${path.resolve(process.argv[1] ?? "")}`) {
  const count = stampDist(path.resolve(target));
  process.stdout.write(`stamped ${count} file(s) under ${target}\n`);
}
