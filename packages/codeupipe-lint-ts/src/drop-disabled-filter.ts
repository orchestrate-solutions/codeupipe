import type { Filter, Payload } from "codeupipe";

import type { Finding } from "./finding.ts";

/**
 * Drops the findings of the rules that the project switched off, from those
 * that are reported and from those that a comment allowed.
 *
 * Input keys: `findings`, `suppressed`, optional `disable` (rule ids).
 * Output keys: `findings`, `suppressed`.
 */
export class DropDisabledFilter implements Filter {
  call(payload: Payload): Payload {
    const disabled = new Set(payload.get<string[]>("disable") ?? []);
    const on = (finding: Finding) => !disabled.has(finding.rule);
    return payload.insert("findings", (payload.get<Finding[]>("findings") ?? []).filter(on))
      .insert("suppressed", (payload.get<Finding[]>("suppressed") ?? []).filter(on));
  }
}
