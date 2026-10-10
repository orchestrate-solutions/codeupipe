import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { methodsOf } from "./primitive-kind.ts";
import { WRITE_OUTSIDE_FILTER, makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";

const READER_METHODS = ["observe", "test", "before", "after", "onError"];
const WRITES = new Set(["insert", "remove", "merge", "withTrace"]);

/** The parameter that holds the Payload: the one named `payload`, else the last one. */
function payloadParameter(method: ts.MethodDeclaration): string | undefined {
  const names = method.parameters.map((parameter) => parameter.name.getText());
  return names.includes("payload") ? "payload" : names[names.length - 1];
}

/**
 * CUP-I004: a write to the Payload from a method that only reads it.
 *
 * Only a Filter writes. A Tap (`observe`), a Predicate (`test`) and a Hook
 * (`before`, `after`, `onError`) read. The runtime does not check, so this
 * rule is the guard. Flagged: `insert`, `remove`, `merge` or `withTrace` on
 * the Payload parameter of such a method; a chain is one finding. Not
 * flagged: a write to `payload.copy()`, and the same method names on any
 * other object.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with CUP-I004 findings appended.
 */
export class AnalyzeOutsideWritesFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      const inMethod = (name: string, method: ts.MethodDeclaration) => {
        const parameter = payloadParameter(method);
        if (parameter === undefined || method.body === undefined) return;
        const writes = (node: ts.Node): node is ts.CallExpression => {
          if (!ts.isCallExpression(node) || !ts.isPropertyAccessExpression(node.expression)
            || !WRITES.has(node.expression.name.text)) {
            return false;
          }
          const owner = node.expression.expression;
          return ts.isIdentifier(owner) ? owner.text === parameter : writes(owner);
        };
        const visit = (node: ts.Node) => {
          if (ts.isFunctionLike(node) || ts.isClassLike(node)) return; // its own scope
          if (writes(node)) {
            const write = (node.expression as ts.PropertyAccessExpression).name.text;
            findings.push(makeFinding(source, node, WRITE_OUTSIDE_FILTER,
              `\`${name}\` writes to the Payload (\`${parameter}.${write}\`)`));
            node.arguments.forEach(visit); // the chain is one finding; its arguments are still checked
            return;
          }
          ts.forEachChild(node, visit);
        };
        ts.forEachChild(method.body, visit);
      };
      const visit = (node: ts.Node) => {
        if (ts.isClassLike(node)) {
          const methods = methodsOf(node);
          for (const name of READER_METHODS) {
            const method = methods.get(name);
            if (method !== undefined) inMethod(name, method);
          }
        }
        ts.forEachChild(node, visit);
      };
      visit(source.tree);
    }
    return payload.insert("findings", findings);
  }
}
