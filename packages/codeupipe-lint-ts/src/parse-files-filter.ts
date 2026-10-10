import { readFileSync } from "node:fs";

import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { PARSE_ERROR, RULES } from "./rules.ts";
import type { Source } from "./source.ts";

/**
 * Reads and parses each file.
 *
 * Input keys: `files`, `findings`, `errors`.
 * Output keys: `sources` (the parsed files), `findings` with CUP-I000 for a
 * file that has a syntax error, `errors` for a file that cannot be read.
 */
export class ParseFilesFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    const errors = [...(payload.get<string[]>("errors") ?? [])];
    const sources: Source[] = [];
    for (const path of payload.get<string[]>("files") ?? []) {
      let text: string;
      try {
        text = readFileSync(path, "utf8");
      } catch (error) {
        errors.push(`${path}: ${error instanceof Error ? error.message : String(error)}`);
        continue;
      }
      const tree = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true);
      const problem = ts.transpileModule(text, { fileName: path, reportDiagnostics: true }).diagnostics?.[0];
      if (problem !== undefined) {
        const at = tree.getLineAndCharacterOfPosition(problem.start ?? 0);
        const what = ts.flattenDiagnosticMessageText(problem.messageText, " ");
        findings.push({
          path, line: at.line + 1, col: at.character + 1, rule: PARSE_ERROR, slug: RULES[PARSE_ERROR] ?? "",
          message: `${what} Fix the syntax error so the file can be checked.`,
        });
        continue;
      }
      sources.push({ path, text, tree });
    }
    return payload.insert("sources", sources).insert("findings", findings).insert("errors", errors);
  }
}
