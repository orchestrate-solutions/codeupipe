import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { methodsOf } from "./primitive-kind.ts";
import { STATE_READ, makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";

const STEP_METHODS = ["call", "test"];
const STATE_MEMBERS = new Set(["executed", "skipped", "errors", "timings", "markExecuted", "markSkipped",
  "recordTiming", "recordError"]);

function isThis(node: ts.Node): boolean {
  return node.kind === ts.SyntaxKind.ThisKeyword;
}

function isStateType(type: ts.TypeNode | undefined): boolean {
  return type !== undefined && ts.isTypeReferenceNode(type) && type.typeName.getText().split(".").pop() === "State";
}

function namesAPipeline(node: ts.Expression): boolean {
  const name = ts.isIdentifier(node) ? node.text : ts.isPropertyAccessExpression(node) ? node.name.text : "";
  return name.toLowerCase().includes("pipeline");
}

/** The properties of a class that hold a State: by their type, or by what the constructor gives them. */
function stateHandles(node: ts.ClassLikeDeclaration): Set<string> {
  const handles = new Set<string>();
  for (const member of node.members) {
    if (ts.isPropertyDeclaration(member) && ts.isIdentifier(member.name)) {
      const start = member.initializer;
      if (isStateType(member.type) || (start !== undefined && ts.isNewExpression(start) && start.expression.getText() === "State")) {
        handles.add(member.name.text);
      }
    }
    if (!ts.isConstructorDeclaration(member) || member.body === undefined) continue;
    const stateParameters = new Set(member.parameters.filter((p) => isStateType(p.type)).map((p) => p.name.getText()));
    const visit = (inner: ts.Node) => {
      if (ts.isBinaryExpression(inner) && inner.operatorToken.kind === ts.SyntaxKind.EqualsToken
        && ts.isPropertyAccessExpression(inner.left) && isThis(inner.left.expression)) {
        const value = inner.right;
        const isState = (ts.isIdentifier(value) && stateParameters.has(value.text))
          || (ts.isPropertyAccessExpression(value) && value.name.text === "state")
          || (ts.isNewExpression(value) && value.expression.getText() === "State");
        if (isState) handles.add(inner.left.name.text);
      }
      ts.forEachChild(inner, visit);
    };
    visit(member.body);
  }
  return handles;
}

/**
 * CUP-I003: a Filter (`call`) or a Predicate (`test`) that reads the State
 * of a pipeline.
 *
 * Flagged: `<x>.state.<member>` where the member is one of State's own,
 * `<pipeline>.state` when the name says it is a pipeline, and a property
 * that holds a State. Not flagged: `this.state` (the step's own property), a
 * Payload key named "state", and anything in a Tap or a Hook.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with CUP-I003 findings appended.
 */
export class AnalyzeStateReadsFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      const inClass = (node: ts.ClassLikeDeclaration) => {
        const handles = stateHandles(node);
        const methods = methodsOf(node);
        for (const name of STEP_METHODS) {
          const body = methods.get(name)?.body;
          if (body !== undefined) inBody(body, handles);
        }
      };
      const reachesState = (node: ts.PropertyAccessExpression, handles: Set<string>): boolean => {
        let outer: string | undefined;
        let at: ts.Expression = node;
        while (ts.isPropertyAccessExpression(at)) {
          if (isThis(at.expression) && handles.has(at.name.text)) return true;
          if (at.name.text === "state" && !isThis(at.expression)
            && ((outer !== undefined && STATE_MEMBERS.has(outer)) || namesAPipeline(at.expression))) {
            return true;
          }
          outer = at.name.text;
          at = at.expression;
        }
        return false;
      };
      const inBody = (body: ts.Node, handles: Set<string>) => {
        const visit = (node: ts.Node) => {
          if (ts.isFunctionLike(node) || ts.isClassLike(node)) return; // its own scope
          if (ts.isPropertyAccessExpression(node) && reachesState(node, handles)) {
            findings.push(makeFinding(source, node, STATE_READ, `Step reads pipeline State (\`${node.getText()}\`)`));
            return;
          }
          ts.forEachChild(node, visit);
        };
        ts.forEachChild(body, visit);
      };
      const visit = (node: ts.Node) => {
        if (ts.isClassLike(node)) inClass(node);
        ts.forEachChild(node, visit);
      };
      visit(source.tree);
    }
    return payload.insert("findings", findings);
  }
}
