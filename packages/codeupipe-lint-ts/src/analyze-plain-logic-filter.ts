import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { isTestFile, primitiveKind } from "./primitive-kind.ts";
import { LOGIC_OUTSIDE_PRIMITIVE, makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";

/** A decision or a loop: the logic that a pipeline is for. */
function isLogic(node: ts.Node): boolean {
  return ts.isIfStatement(node) || ts.isConditionalExpression(node) || ts.isSwitchStatement(node)
    || ts.isForStatement(node) || ts.isForInStatement(node) || ts.isForOfStatement(node)
    || ts.isWhileStatement(node) || ts.isDoStatement(node) || ts.isTryStatement(node);
}

function hasLogic(node: ts.Node): boolean {
  let found = false;
  const visit = (inner: ts.Node) => {
    if (found) return;
    if (isLogic(inner)) {
      found = true;
      return;
    }
    ts.forEachChild(inner, visit);
  };
  visit(node);
  return found;
}

const WHAT = "has logic and is not a Filter, a Predicate, a Tap, a Hook or a Pipeline";

/**
 * CUP-I008, a warning: logic that is not in a primitive.
 *
 * A project that uses codeupipe writes its logic as Filters, Predicates,
 * Taps, Hooks and Pipelines. Logic in a plain function or a plain class works
 * as well, so nothing else shows the mistake. This rule shows it.
 *
 * Logic is a decision or a loop: `if`, `? :`, `switch`, `for`, `while`,
 * `do`, `try`. Flagged, once each: a function at the top of a file, a class
 * at the top of a file that is not a primitive, and the code at the top of a
 * file itself. Not flagged: a primitive (its logic is where it must be), a
 * function or a class with no logic, a type, and a test file. Not seen: a
 * loop that is a method call (`map`, `filter`, `forEach`), and `&&` / `||`.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with CUP-I008 warnings appended.
 */
export class AnalyzePlainLogicFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      if (isTestFile(source.path)) continue;
      let moduleCode: ts.Node | undefined;
      for (const statement of source.tree.statements) {
        if (ts.isFunctionDeclaration(statement)) {
          if (statement.body !== undefined && hasLogic(statement.body)) {
            findings.push(makeFinding(source, statement.name ?? statement, LOGIC_OUTSIDE_PRIMITIVE,
              `Function \`${statement.name?.text ?? "default"}\` ${WHAT}`));
          }
        } else if (ts.isClassDeclaration(statement)) {
          if (primitiveKind(statement) === undefined && hasLogic(statement)) {
            findings.push(makeFinding(source, statement.name ?? statement, LOGIC_OUTSIDE_PRIMITIVE,
              `Class \`${statement.name?.text ?? "default"}\` ${WHAT}`));
          }
        } else if (ts.isVariableStatement(statement)) {
          for (const declaration of statement.declarationList.declarations) {
            const value = declaration.initializer;
            if (value === undefined) continue;
            if (ts.isArrowFunction(value) || ts.isFunctionExpression(value)) {
              if (hasLogic(value.body)) {
                findings.push(makeFinding(source, declaration.name, LOGIC_OUTSIDE_PRIMITIVE,
                  `Function \`${declaration.name.getText()}\` ${WHAT}`));
              }
            } else if (moduleCode === undefined && hasLogic(value)) {
              moduleCode = declaration;
            }
          }
        } else if (ts.isInterfaceDeclaration(statement) || ts.isTypeAliasDeclaration(statement)
          || ts.isImportDeclaration(statement) || ts.isExportDeclaration(statement)) {
          // no logic
        } else if (moduleCode === undefined && (isLogic(statement) || hasLogic(statement))) {
          moduleCode = statement;
        }
      }
      if (moduleCode !== undefined) {
        findings.push(makeFinding(source, moduleCode, LOGIC_OUTSIDE_PRIMITIVE, `The code at the top of this file ${WHAT}`));
      }
    }
    return payload.insert("findings", findings);
  }
}
