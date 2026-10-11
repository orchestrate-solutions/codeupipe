import type { Filter, Payload } from "codeupipe";

import { formatFinding } from "./finding.ts";
import type { Finding } from "./finding.ts";

/**
 * The findings as sorted report lines, and the exit code.
 *
 * Input keys: `findings`, `suppressed`, `errors`, optional `strict`.
 * Output keys: `findings` (sorted), `report` (text for stdout),
 * `errorReport` (text for stderr), `exitCode`: 0 no findings, 1 findings,
 * 2 a path could not be read, so the check is not complete.
 *
 * A warning is in the report and is counted apart. It does not make the
 * exit code 1, unless `strict` is true.
 */
export class FormatReportFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])].sort((a, b) =>
      (a.path < b.path ? -1 : a.path > b.path ? 1 : 0) || a.line - b.line || a.col - b.col
      || (a.rule < b.rule ? -1 : a.rule > b.rule ? 1 : 0));
    const suppressed = payload.get<Finding[]>("suppressed") ?? [];
    const errors = payload.get<string[]>("errors") ?? [];
    const lines = findings.map(formatFinding);
    const warnings = findings.filter((finding) => finding.severity === "warning").length;
    const real = findings.length - warnings;
    let summary = real === 0 ? "No findings" : `${real} ${real === 1 ? "finding" : "findings"}`;
    if (suppressed.length > 0) summary += ` (${suppressed.length} suppressed)`;
    summary += ".";
    if (warnings > 0) summary += ` ${warnings} ${warnings === 1 ? "warning" : "warnings"}.`;
    lines.push(summary);
    const fails = real > 0 || (warnings > 0 && payload.get("strict") === true);
    return payload.insert("findings", findings).insert("report", lines.join("\n"))
      .insert("errorReport", errors.map((error) => "error: " + error).join("\n"))
      .insert("exitCode", errors.length > 0 ? 2 : fails ? 1 : 0);
  }
}
