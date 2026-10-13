import type { Filter, Payload } from "codeupipe";

import type { Finding } from "./finding.ts";
import type { Source } from "./source.ts";

const ANONYMOUS = /cup:\s*allow-anonymous\b/;
const INVARIANT = /cup:\s*allow-(state-read|outside-write|shared-file|name|plain)\b/;
const COMMENT_ONLY = /^\s*(\/\/|\/\*|\*)/;

/**
 * Drops the findings that a comment allows.
 *
 * `// cup: allow-anonymous` allows a CUP-A finding. `// cup: allow-state-read`,
 * `allow-outside-write`, `allow-shared-file`, `allow-name` and `allow-plain`
 * allow a CUP-I finding. The comment is on the line of the finding, on the line of the
 * `add...` call around it, or alone on the line directly above. Any text can
 * follow the marker.
 *
 * Input keys: `findings`, `sources`.
 * Output keys: `findings` (kept), `suppressed` (dropped), `usedMarkers` (the
 * place of each comment that allowed a finding, as `path:line`).
 */
export class ApplySuppressionsFilter implements Filter {
  call(payload: Payload): Payload {
    const lines = new Map<string, string[]>();
    for (const source of payload.get<Source[]>("sources") ?? []) {
      lines.set(source.path, source.text.split(/\r?\n/));
    }
    const kept: Finding[] = [];
    const suppressed: Finding[] = [];
    const used = new Set<string>();
    for (const finding of payload.get<Finding[]>("findings") ?? []) {
      const marker = finding.rule.startsWith("CUP-A") ? ANONYMOUS : INVARIANT;
      const text = lines.get(finding.path) ?? [];
      const line = (number: number | undefined) => (number === undefined ? "" : text[number - 1] ?? "");
      const above = line(finding.line - 1);
      const places = [finding.line, finding.callLine].filter((number) => marker.test(line(number)));
      if (COMMENT_ONLY.test(above) && marker.test(above)) places.push(finding.line - 1);
      for (const place of places) used.add(`${finding.path}:${place}`);
      (places.length > 0 ? suppressed : kept).push(finding);
    }
    return payload.insert("findings", kept).insert("suppressed", suppressed).insert("usedMarkers", [...used]);
  }
}
