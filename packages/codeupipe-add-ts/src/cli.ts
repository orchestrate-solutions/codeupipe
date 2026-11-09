#!/usr/bin/env node
/**
 * `codeupipe add <kind> <name> [dir] [--description TEXT]`
 *
 * The command line of the command (conformance/ADD.md). The work is the
 * pipeline in add.ts: this file only reads the arguments, says what happened,
 * and gives the exit code.
 */
import { main } from "./add.ts";

process.exitCode = await main(process.argv.slice(2));
