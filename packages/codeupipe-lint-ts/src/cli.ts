#!/usr/bin/env node
/**
 * codeupipe-lint [--exclude GLOB] [--disable RULE] [--config FILE] [--rules] [paths...]
 *
 * With no paths, they come from cup.config.json. Exit code: 0 no findings,
 * 1 findings, 2 a path could not be read or the arguments cannot be used.
 */
import { parseArgs } from "node:util";

import { lintPaths } from "./lint-paths.ts";
import { CONFIG_NAME, readLintConfig } from "./read-config.ts";
import { RULES } from "./rules.ts";

async function main(argv: string[]): Promise<number> {
  let args;
  try {
    args = parseArgs({
      args: argv, allowPositionals: true,
      options: {
        exclude: { type: "string", multiple: true },
        disable: { type: "string", multiple: true },
        config: { type: "string" },
        rules: { type: "boolean" },
      },
    });
  } catch (error) {
    console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  if (args.values.rules) {
    for (const rule of Object.keys(RULES).sort()) console.log(`${rule}  ${RULES[rule]}`);
    return 0;
  }

  let paths = args.positionals;
  let exclude = args.values.exclude;
  let disable = args.values.disable;
  if (paths.length === 0) {
    // The file stands in for the arguments only when no paths are given: a
    // path that someone names is checked, whatever the file excludes.
    try {
      const lint = readLintConfig(args.values.config) ?? {};
      paths = lint.paths ?? [];
      exclude = exclude ?? lint.exclude;
      disable = disable ?? lint.disable;
    } catch (error) {
      console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
      return 2;
    }
  }
  if (paths.length === 0) {
    console.error(`error: give at least one path, or list them under lint.paths in ${CONFIG_NAME}`);
    return 2;
  }
  const unknown = (disable ?? []).filter((rule) => RULES[rule] === undefined);
  if (unknown.length > 0) {
    console.error(`error: no such rule: ${unknown.join(", ")} (the rules are listed by --rules)`);
    return 2;
  }

  const out = await lintPaths(paths, { exclude, disable });
  console.log(out.get<string>("report"));
  const errorReport = out.get<string>("errorReport");
  if (errorReport) console.error(errorReport);
  return out.get<number>("exitCode") ?? 2;
}

process.exitCode = await main(process.argv.slice(2));
