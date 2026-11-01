// The command line: it reads argv and gives the exit code. See the cup: allow-plain comments on the two functions below.
/**
 * `codeupipe add <kind> <name> [dir] [--description TEXT]`
 * `codeupipe add --layout cup.layout.yaml`
 *
 * Makes the component file and the test file of one component, or of each
 * component of a layout, in the directory where it runs (conformance/ADD.md).
 * Prints each file that it made.
 *
 * Exit code: 0 the files are made, 1 a file exists (nothing is written), 2 the
 * arguments cannot be used (nothing is written). With --layout, a file that
 * exists is kept, and the exit code is 0.
 */
import { cwd } from "node:process";

import { Payload } from "codeupipe";

import { AddPipeline } from "./add-pipeline.ts";
import { Refusal } from "./add-refusal.ts";
import { LayoutPipeline } from "./layout-pipeline.ts";

export type Request = { kind: string; name: string; directory: string; description: string };

/** `--layout FILE`: the components are in the file. */
export type LayoutRequest = { layout: string };

const USAGE = "usage: codeupipe add <kind> <name> [dir] [--description TEXT]\n       codeupipe add --layout FILE";
const LAYOUT_ALONE = "--layout takes no kind, name, dir or --description: they are in the layout.";

/** The arguments, or a text that says why the command cannot use them. cup: allow-plain the reading of argv is the shell of the command, not its logic. */
export function parseArguments(argv: string[]): Request | LayoutRequest | string {
  let kind: string | undefined;
  let name: string | undefined;
  let directory: string | undefined;
  let description: string | undefined;
  let layout: string | undefined;
  for (let i = 0; i < argv.length; i++) {
    const argument = argv[i] ?? "";
    if (argument === "--description") {
      description = argv[++i] ?? "";
    } else if (argument.startsWith("--description=")) {
      description = argument.slice("--description=".length);
    } else if (argument === "--layout") {
      layout = argv[++i];
      if (layout === undefined) return USAGE;
    } else if (argument.startsWith("--layout=")) {
      layout = argument.slice("--layout=".length);
    } else if (argument.startsWith("-") && argument !== "-") {
      return USAGE;
    } else if (kind === undefined) {
      kind = argument;
    } else if (name === undefined) {
      name = argument;
    } else if (directory === undefined) {
      directory = argument;
    } else {
      return USAGE;
    }
  }
  if (layout !== undefined) return kind === undefined && description === undefined ? { layout } : LAYOUT_ALONE;
  if (kind === undefined || name === undefined) return USAGE;
  return { kind, name, directory: directory ?? ".", description: description ?? "" };
}

/** Run the pipeline of `add`, and return the exit code. */
export async function add(request: Request, root = cwd()): Promise<string[]> {
  const out = await new AddPipeline().run(new Payload({ root, ...request }));
  return out.get<string[]>("written") ?? [];
}

/** Run the pipeline of `add --layout`: the files that it wrote, kept, and kept with steps that changed. */
export async function addLayout(request: LayoutRequest, root = cwd()):
  Promise<{ written: string[]; kept: string[]; stale: string[] }> {
  const out = await new LayoutPipeline().run(new Payload({ root, layout_path: request.layout }));
  return {
    written: out.get<string[]>("written") ?? [],
    kept: out.get<string[]>("kept") ?? [],
    stale: out.get<string[]>("stale") ?? [],
  };
}

// cup: allow-plain the command line reads argv, prints, and gives the exit code; the logic is in the pipeline.
export async function main(argv: string[]): Promise<number> {
  const request = parseArguments(argv);
  if (typeof request === "string") {
    console.error(request);
    return 2;
  }
  try {
    if ("layout" in request) {
      const { written, kept, stale } = await addLayout(request);
      for (const path of kept) {
        console.error(stale.includes(path)
          ? `${path} exists, kept, and its steps are not those of the layout. Change the file: the command does not `
            + "write it again."
          : `${path} exists, kept`);
      }
      for (const path of written) console.log(path);
      return 0;
    }
    for (const path of await add(request)) console.log(path);
  } catch (error) {
    if (!(error instanceof Refusal)) throw error;
    console.error(error.message);
    return error.exitCode;
  }
  return 0;
}
