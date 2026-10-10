import ts from "typescript";

import {
  FUNCTION_PREDICATE, FUNCTION_STEP, LOCAL_TYPE_STEP, NAMED_FUNCTION_STEP, OBJECT_LITERAL_STEP, UNNAMED_PIPELINE,
} from "./rules.ts";

export type Role = "Filter" | "Tap" | "Pipeline" | "Valve predicate" | "Valve filter";

/** A rule, and the words that say what the value is: `is a function`. */
export type Verdict = { rule: string; what: string };

function unwrap(node: ts.Expression): ts.Expression {
  let inner = node;
  while (ts.isParenthesizedExpression(inner) || ts.isAsExpression(inner) || ts.isNonNullExpression(inner)
    || ts.isSatisfiesExpression(inner)) {
    inner = inner.expression;
  }
  return inner;
}

function isScope(node: ts.Node): boolean {
  return ts.isSourceFile(node) || ts.isFunctionLike(node) || ts.isModuleBlock(node) || ts.isClassStaticBlockDeclaration(node);
}

/** The declarations of `name` that the scope `scope` holds itself, not in a function inside it. */
function declarationsIn(scope: ts.Node, name: string): ts.Node[] {
  const found: ts.Node[] = [];
  if (ts.isFunctionLike(scope)) {
    for (const parameter of scope.parameters) {
      if (parameter.getText().includes(name)) found.push(parameter);
    }
  }
  const visit = (node: ts.Node) => {
    if (ts.isVariableDeclaration(node) || ts.isBindingElement(node)) {
      if (ts.isIdentifier(node.name) ? node.name.text === name : node.name.getText().includes(name)) found.push(node);
    } else if ((ts.isFunctionDeclaration(node) || ts.isClassDeclaration(node)) && node.name?.text === name) {
      found.push(node);
    } else if ((ts.isImportClause(node) || ts.isImportSpecifier(node) || ts.isNamespaceImport(node))
      && node.name?.text === name) {
      found.push(node);
    } else if (ts.isCatchClause(node) && node.variableDeclaration?.name.getText() === name) {
      found.push(node);
    }
    if (node !== scope && isScope(node)) return;
    ts.forEachChild(node, visit);
  };
  ts.forEachChild(scope, visit);
  return found;
}

/**
 * The one declaration that `name` has at `from`, by the rules of scope: the
 * nearest function outwards to the file. Undefined when the file does not
 * bind the name, or binds it in a way that this linter does not follow.
 */
function resolve(name: ts.Identifier): ts.Node | undefined {
  for (let scope: ts.Node | undefined = name.parent; scope !== undefined; scope = scope.parent) {
    if (!isScope(scope)) continue;
    const found = declarationsIn(scope, name.text);
    if (found.length === 1) return found[0];
    if (found.length > 1) return undefined;
  }
  return undefined;
}

function isInsideFunction(node: ts.Node): boolean {
  for (let parent = node.parent; parent !== undefined; parent = parent.parent) {
    if (ts.isFunctionLike(parent)) return true;
  }
  return false;
}

function isConst(declaration: ts.VariableDeclaration): boolean {
  return ts.isVariableDeclarationList(declaration.parent) && (declaration.parent.flags & ts.NodeFlags.Const) !== 0;
}

/**
 * What is wrong with a value that is given as a step, or undefined.
 *
 * A name is followed to its declaration in the same file when that is a
 * `const`, a function or a class. A `let`, a parameter, an import and the
 * result of a call are not followed.
 */
export function classifyStep(expression: ts.Expression, role: Role, seen: Set<ts.Node> = new Set()): Verdict | undefined {
  const node = unwrap(expression);
  if (seen.has(node)) return undefined;
  seen.add(node);

  if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
    return { rule: FUNCTION_STEP, what: "is a function" };
  }
  if (ts.isObjectLiteralExpression(node)) {
    return { rule: OBJECT_LITERAL_STEP, what: "is an object literal" };
  }
  if (ts.isNewExpression(node)) {
    const type = unwrap(node.expression);
    if (ts.isClassExpression(type)) {
      return { rule: LOCAL_TYPE_STEP, what: "is an instance of a class with no name" };
    }
    if (ts.isIdentifier(type)) {
      if (type.text === "Pipeline" && role === "Pipeline") {
        return { rule: UNNAMED_PIPELINE, what: "is a plain `new Pipeline()`" };
      }
      const declaration = resolve(type);
      if (declaration !== undefined && ts.isClassDeclaration(declaration) && isInsideFunction(declaration)) {
        return { rule: LOCAL_TYPE_STEP, what: `is an instance of \`${type.text}\`, a class that is declared in a function` };
      }
    }
    return undefined;
  }
  if (ts.isIdentifier(node)) {
    const declaration = resolve(node);
    if (declaration === undefined) return undefined;
    if (ts.isFunctionDeclaration(declaration)) {
      return role === "Valve predicate"
        ? { rule: FUNCTION_PREDICATE, what: `\`${node.text}\` is a function, not a predicate object` }
        : { rule: NAMED_FUNCTION_STEP, what: `\`${node.text}\` is a function` };
    }
    if (ts.isVariableDeclaration(declaration) && isConst(declaration) && declaration.initializer !== undefined) {
      const verdict = classifyStep(declaration.initializer, role, seen);
      return verdict === undefined ? undefined : { rule: verdict.rule, what: `\`${node.text}\` ${verdict.what}` };
    }
  }
  return undefined;
}
