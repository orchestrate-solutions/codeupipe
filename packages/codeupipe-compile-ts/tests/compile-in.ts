// A helper for the tests: write source files to a new directory and compile one pipeline class.
import { mkdtempSync, realpathSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { compile } from "../src/index.ts";

export const PIPELINE_IMPORT = `import { Pipeline } from "codeupipe";\n`;

export type Compiled = { code: string; outFile: string; run(input: Record<string, unknown>): Promise<Record<string, unknown>> };

export function project(files: Record<string, string>): string {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "cup-compile-")));
  for (const [name, text] of Object.entries(files)) writeFileSync(join(root, name), text);
  return root;
}

/** Compile `className` of `pipeline.ts` and import the module that was written. */
export async function compileIn(files: Record<string, string>, className = "MainPipeline"): Promise<Compiled> {
  const root = project(files);
  const outFile = join(root, "compiled.ts");
  const code = await compile(join(root, "pipeline.ts"), className, { outFile });
  const module: { run: Compiled["run"] } = await import(pathToFileURL(outFile).href);
  return { code, outFile, run: module.run };
}
