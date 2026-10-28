import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { Payload } from "codeupipe";

import { CompilePipeline } from "./compile-pipeline.ts";
import { realPath } from "./real-path.ts";
import { clearSources } from "./source-files.ts";

/**
 * Write the pipeline class `className` of `file` as one plain TypeScript
 * module, and return its text. With `outFile`, the module is written there
 * and its imports are relative to that place.
 *
 * Throws CompileRefusal for a pipeline that has no plain form. Nothing is
 * written then.
 */
export async function compile(file: string, className: string, options: { outFile?: string } = {}): Promise<string> {
  clearSources();
  const outFile = options.outFile === undefined ? undefined : realPath(options.outFile);
  const out = await new CompilePipeline().run(new Payload({ file: resolve(file), className, outFile: outFile ?? null }));
  const code = out.get<string>("code") ?? "";
  if (outFile !== undefined) {
    mkdirSync(dirname(outFile), { recursive: true });
    writeFileSync(outFile, code);
  }
  return code;
}
