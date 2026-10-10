#!/usr/bin/env node
/**
 * codeupipe-compile FILE:ClassName --out FILE
 *
 * Exit code: 0 the module is written, 1 the pipeline is refused (the message
 * names the place and the fix), 2 the command could not run. Nothing is
 * written on 1 or 2.
 */
import { parseArgs } from "node:util";

import { compile } from "./compile.ts";
import { CompileRefusal } from "./compile-refusal.ts";

async function main(argv: string[]): Promise<number> {
  let target: string | undefined;
  let outFile: string | undefined;
  try {
    const args = parseArgs({ args: argv, allowPositionals: true, options: { out: { type: "string" } } });
    target = args.positionals[0];
    outFile = args.values.out;
    if (args.positionals.length !== 1) target = undefined;
  } catch (error) {
    console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  const colon = target?.lastIndexOf(":") ?? -1;
  if (target === undefined || outFile === undefined || colon <= 0 || colon === target.length - 1) {
    console.error("usage: codeupipe-compile FILE:ClassName --out FILE");
    return 2;
  }
  try {
    await compile(target.slice(0, colon), target.slice(colon + 1), { outFile });
  } catch (error) {
    if (error instanceof CompileRefusal) {
      console.error(`refused: ${error.message}`);
      return 1;
    }
    console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  console.log(outFile);
  return 0;
}

process.exitCode = await main(process.argv.slice(2));
