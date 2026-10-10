/**
 * One finding, at `path:line:col` (line and column start at 1).
 *
 * `callLine` is the line of the `add...` call around the finding, when it is
 * a different line: a comment that suppresses can be on that line too.
 */
export type Finding = {
  path: string;
  line: number;
  col: number;
  rule: string;
  slug: string;
  message: string;
  callLine?: number;
};

export function formatFinding(finding: Finding): string {
  return `${finding.path}:${finding.line}:${finding.col}  ${finding.rule} ${finding.slug}  ${finding.message}`;
}
