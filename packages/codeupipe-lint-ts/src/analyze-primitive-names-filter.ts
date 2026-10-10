import { basename } from "node:path";

import type { Filter, Payload } from "codeupipe";

import type { Finding } from "./finding.ts";
import { isTestFile, topLevelPrimitives } from "./primitive-kind.ts";
import { PRIMITIVE_FILE_NAME, PRIMITIVE_ROLE_SUFFIX, makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";

/** `ParseHTMLFilter` gives `parse-html-filter`. */
export function kebabCase(className: string): string {
  return className.replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, "-").toLowerCase();
}

/**
 * CUP-I007: the class name of a primitive ends with its role
 * (`DiscountFilter`, `AuditTap`, `PrintStepsHook`, `AtLeastPredicate`,
 * `PricingPipeline`).
 *
 * CUP-I006: the file name is the class name in kebab-case
 * (`discount-filter.ts`).
 *
 * Checked: primitive classes at the top level of a file. Not checked: plain
 * classes, and test files.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with CUP-I006 and CUP-I007 findings appended.
 */
export class AnalyzePrimitiveNamesFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      if (isTestFile(source.path)) continue;
      const file = basename(source.path);
      const dot = file.indexOf(".");
      const stem = dot === -1 ? file : file.slice(0, dot);
      const extension = dot === -1 ? "" : file.slice(dot);
      for (const { node, name, kind } of topLevelPrimitives(source.tree)) {
        const at = node.name ?? node;
        let wanted = name;
        if (!name.endsWith(kind)) {
          wanted = name + kind;
          findings.push(makeFinding(source, at, PRIMITIVE_ROLE_SUFFIX,
            `${kind} \`${name}\` does not say what it is. Name it \`${wanted}\``));
        }
        if (stem !== kebabCase(wanted)) {
          findings.push(makeFinding(source, at, PRIMITIVE_FILE_NAME,
            `\`${wanted}\` is in \`${file}\`. Put it in \`${kebabCase(wanted)}${extension}\``));
        }
      }
    }
    return payload.insert("findings", findings);
  }
}
