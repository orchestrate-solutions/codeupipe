import type { Filter, Payload } from "codeupipe";

import { formatFinding } from "./finding.ts";
import type { Finding } from "./finding.ts";

/**
 * The findings as sorted report lines, and the exit code.
 *
 * Input keys: `findings`, `suppressed`, `errors`.
 * Output keys: `findings` (sorted), `report` (text for stdout),
 * `errorReport` (text for stderr), `exitCode`: 0 no findings, 1 findings,
 * 2 a path could not be read, so the check is not complete.
 */
export class FormatReportFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])].sort((a, b) =>
      (a.path < b.path ? -1 : a.path > b.path ? 1 : 0) || a.line - b.line || a.col - b.col
      || (a.rule < b.rule ? -1 : a.rule > b.rule ? 1 : 0));
    const suppressed = payload.get<Finding[]>("suppressed") ?? [];
    const errors = payload.get<string[]>("errors") ?? [];
    const lines = findings.map(formatFinding);
    let summary = findings.length === 0 ? "No findings" : `${findings.length} ${findings.length === 1 ? "finding" : "findings"}`;
    if (suppressed.length > 0) summary += ` (${suppressed.length} suppressed)`;
    lines.push(summary + ".");
    return payload.insert("findings", findings).insert("report", lines.join("\n"))
      .insert("errorReport", errors.map((error) => "error: " + error).join("\n"))
      .insert("exitCode", errors.length > 0 ? 2 : findings.length > 0 ? 1 : 0);
  }
}
