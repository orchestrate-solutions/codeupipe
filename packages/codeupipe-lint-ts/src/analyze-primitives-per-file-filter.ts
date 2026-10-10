import type { Filter, Payload } from "codeupipe";

import type { Finding } from "./finding.ts";
import { isTestFile, topLevelPrimitives } from "./primitive-kind.ts";
import { ONE_PRIMITIVE_PER_FILE, makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";

/**
 * CUP-I005: one primitive in each file.
 *
 * Flagged: each primitive class at the top level of a file after the first.
 * Not flagged: plain classes and functions beside the primitive, classes in
 * a function, and test files.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with CUP-I005 findings appended.
 */
export class AnalyzePrimitivesPerFileFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      if (isTestFile(source.path)) continue;
      const [first, ...rest] = topLevelPrimitives(source.tree);
      if (first === undefined) continue;
      for (const other of rest) {
        findings.push(makeFinding(source, other.node.name ?? other.node, ONE_PRIMITIVE_PER_FILE,
          `${other.kind} \`${other.name}\` shares this file with ${first.kind} \`${first.name}\``));
      }
    }
    return payload.insert("findings", findings);
  }
}
