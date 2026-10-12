import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { fixOf, MARKER_ALLOWS_NOTHING, RULES } from "./rules.ts";
import type { Source } from "./source.ts";

const MARKER = /^cup:\s*(allow-[\w-]*)/;

/**
 * Finds each `cup: allow-...` comment that allowed no finding (CUP-I009, a
 * warning). Such a comment stays when the code that it was for is gone or
 * has moved, or when its kind has a spelling error.
 *
 * Only a comment that starts with the marker counts, so text that names a
 * marker in a string or in the middle of a sentence is not reported.
 *
 * Input keys: `findings`, `sources`, `usedMarkers` (from ApplySuppressionsFilter).
 * Output keys: `findings`.
 */
export class AnalyzeStaleMarkersFilter implements Filter {
  call(payload: Payload): Payload {
    const used = new Set(payload.get<string[]>("usedMarkers") ?? []);
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      for (const marker of this.markersOf(source)) {
        if (used.has(`${source.path}:${marker.line}`)) continue;
        findings.push({
          path: source.path, line: marker.line, col: marker.col, rule: MARKER_ALLOWS_NOTHING, slug: RULES[MARKER_ALLOWS_NOTHING] ?? "",
          message: `The comment \`cup: ${marker.kind}\` allows nothing. ${fixOf(MARKER_ALLOWS_NOTHING)}`, severity: "warning",
        });
      }
    }
    findings.sort((a, b) => a.path.localeCompare(b.path) || a.line - b.line || a.col - b.col);
    return payload.insert("findings", findings);
  }

  /** Each line of a comment of the file that starts with a marker. */
  markersOf(source: Source): Array<{ line: number; col: number; kind: string }> {
    const ranges = new Map<number, ts.CommentRange>();
    const visit = (node: ts.Node) => {
      const found = [
        ...(ts.getLeadingCommentRanges(source.text, node.getFullStart()) ?? []),
        ...(ts.getTrailingCommentRanges(source.text, node.getEnd()) ?? []),
      ];
      for (const range of found) ranges.set(range.pos, range);
      // The text of a string or a template can look like a comment. It has no tokens to look in.
      if (!ts.isStringLiteralLike(node) && !ts.isTemplateExpression(node)) node.getChildren(source.tree).forEach(visit);
    };
    visit(source.tree);

    const markers: Array<{ line: number; col: number; kind: string }> = [];
    for (const range of [...ranges.values()].sort((a, b) => a.pos - b.pos)) {
      let at = range.pos;
      for (const text of source.text.slice(range.pos, range.end).split("\n")) {
        const lead = /^\s*(\/\/+|\/\*+|\*(?!\/))?\s*/.exec(text)?.[0].length ?? 0;
        const kind = MARKER.exec(text.slice(lead))?.[1];
        if (kind !== undefined) {
          const place = source.tree.getLineAndCharacterOfPosition(at + lead);
          markers.push({ line: place.line + 1, col: place.character + 1, kind });
        }
        at += text.length + 1;
      }
    }
    return markers;
  }
}
