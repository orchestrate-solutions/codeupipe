// The command line: it reads argv and gives the exit code. See the cup: allow-plain comments on the two functions below.
/**
 * `codeupipe add <kind> <name> [dir] [--description TEXT]`
 *
 * Makes the component file and the test file of one component, in the
 * directory where it runs (conformance/ADD.md). Prints each file that it made.
 *
 * Exit code: 0 the files are made, 1 a file exists (nothing is written), 2 the
 * arguments cannot be used (nothing is written).
 */
import { cwd } from "node:process";

import { Payload } from "codeupipe";

import { AddPipeline } from "./add-pipeline.ts";
import { Refusal } from "./add-refusal.ts";

export type Request = { kind: string; name: string; directory: string; description: string };

/** The arguments, or undefined for a shape that the command cannot use. cup: allow-plain the reading of argv is the shell of the command, not its logic. */
export function parseArguments(argv: string[]): Request | undefined {
  let kind: string | undefined;
  let name: string | undefined;
  let directory: string | undefined;
  let description = "";
  for (let i = 0; i < argv.length; i++) {
    const argument = argv[i] ?? "";
    if (argument === "--description") {
      description = argv[++i] ?? "";
    } else if (argument.startsWith("--description=")) {
      description = argument.slice("--description=".length);
    } else if (argument.startsWith("-") && argument !== "-") {
      return undefined;
    } else if (kind === undefined) {
      kind = argument;
    } else if (name === undefined) {
      name = argument;
    } else if (directory === undefined) {
      directory = argument;
    } else {
      return undefined;
    }
  }
  if (kind === undefined || name === undefined) return undefined;
  return { kind, name, directory: directory ?? ".", description };
}

/** Run the pipeline of `add`, and return the exit code. */
export async function add(request: Request, root = cwd()): Promise<string[]> {
  const out = await new AddPipeline().run(new Payload({ root, ...request }));
  return out.get<string[]>("written") ?? [];
}

// cup: allow-plain the command line reads argv, prints, and gives the exit code; the logic is in the pipeline.
export async function main(argv: string[]): Promise<number> {
  const request = parseArguments(argv);
  if (request === undefined) {
    console.error("usage: codeupipe add <kind> <name> [dir] [--description TEXT]");
    return 2;
  }
  try {
    for (const path of await add(request)) console.log(path);
  } catch (error) {
    if (!(error instanceof Refusal)) throw error;
    console.error(error.message);
    return error.exitCode;
  }
  return 0;
}
