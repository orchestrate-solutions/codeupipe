import { Payload } from "codeupipe";

import { LintPipeline } from "./lint-pipeline.ts";

/**
 * Run the linter over `paths`. The Payload that comes back holds `findings`,
 * `suppressed`, `errors`, `report`, `errorReport` and `exitCode`.
 */
export function lintPaths(paths: string[], options: { exclude?: string[]; disable?: string[]; strict?: boolean } = {}): Promise<Payload> {
  return new LintPipeline().run(new Payload({
    paths, findings: [], errors: [], exclude: options.exclude ?? [], disable: options.disable ?? [], strict: options.strict === true,
  }));
}
