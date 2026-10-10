import type { Filter, Payload } from "codeupipe";

import type { Finding } from "./finding.ts";

/**
 * Drops the findings of the rules that the project switched off.
 *
 * Input keys: `findings`, optional `disable` (rule ids).
 * Output keys: `findings`.
 */
export class DropDisabledFilter implements Filter {
  call(payload: Payload): Payload {
    const disabled = new Set(payload.get<string[]>("disable") ?? []);
    const findings = payload.get<Finding[]>("findings") ?? [];
    return payload.insert("findings", findings.filter((finding) => !disabled.has(finding.rule)));
  }
}
