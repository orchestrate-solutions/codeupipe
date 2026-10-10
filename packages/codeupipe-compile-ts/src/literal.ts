import ts from "typescript";

/**
 * Whether an expression is a literal: text, a number, true, false, null,
 * undefined, or a list or an object of literals. The compiler writes such a
 * value into the code as a constant.
 */
export function isLiteral(node: ts.Expression): boolean {
  if (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isSatisfiesExpression(node)) {
    return isLiteral(node.expression);
  }
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) || ts.isNumericLiteral(node)
    || ts.isBigIntLiteral(node)) {
    return true;
  }
  if (node.kind === ts.SyntaxKind.TrueKeyword || node.kind === ts.SyntaxKind.FalseKeyword
    || node.kind === ts.SyntaxKind.NullKeyword) {
    return true;
  }
  if (ts.isIdentifier(node)) return node.text === "undefined";
  if (ts.isPrefixUnaryExpression(node)) {
    return (node.operator === ts.SyntaxKind.MinusToken || node.operator === ts.SyntaxKind.PlusToken)
      && ts.isNumericLiteral(node.operand);
  }
  if (ts.isArrayLiteralExpression(node)) return node.elements.every((element) => isLiteral(element));
  if (ts.isObjectLiteralExpression(node)) {
    return node.properties.every((property) => ts.isPropertyAssignment(property)
      && (ts.isIdentifier(property.name) || ts.isStringLiteral(property.name) || ts.isNumericLiteral(property.name))
      && isLiteral(property.initializer));
  }
  return false;
}
