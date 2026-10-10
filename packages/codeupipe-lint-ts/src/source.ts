import ts from "typescript";

/** One parsed file. */
export type Source = { path: string; text: string; tree: ts.SourceFile };

/** The line and column of a node, from 1. */
export function position(source: Source, node: ts.Node): { line: number; col: number } {
  const at = source.tree.getLineAndCharacterOfPosition(node.getStart(source.tree));
  return { line: at.line + 1, col: at.character + 1 };
}
