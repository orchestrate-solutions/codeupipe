import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import type { Finding } from "./finding.ts";
import { makeFinding } from "./rules.ts";
import type { Source } from "./source.ts";
import { classifyStep } from "./step-classifier.ts";
import type { Role } from "./step-classifier.ts";

const STEP_METHODS: Record<string, Role> = { addFilter: "Filter", addTap: "Tap", addPipeline: "Pipeline" };
const VALVE_ROLES: Role[] = ["Valve predicate", "Valve filter"];

/**
 * CUP-A001, A002, A003, A005, A008, A009: a step that has no name.
 *
 * A step is the argument of `addFilter`, `addTap` or `addPipeline` (on any
 * receiver), or one of the two arguments of `addValve(predicate, filter)`.
 *
 * Input keys: `sources`, `findings`.
 * Output keys: `findings`, with the new findings appended.
 */
export class AnalyzeStepsFilter implements Filter {
  call(payload: Payload): Payload {
    const findings = [...(payload.get<Finding[]>("findings") ?? [])];
    for (const source of payload.get<Source[]>("sources") ?? []) {
      const visit = (node: ts.Node) => {
        if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
          const method = node.expression.name.text;
          const roles = method === "addValve" ? VALVE_ROLES
            : STEP_METHODS[method] !== undefined ? [STEP_METHODS[method]] : [];
          roles.forEach((role, index) => {
            const argument = node.arguments[index];
            const verdict = argument === undefined ? undefined : classifyStep(argument, role);
            if (argument !== undefined && verdict !== undefined) {
              findings.push(makeFinding(source, argument, verdict.rule, `${role} ${verdict.what}`, node));
            }
          });
        }
        ts.forEachChild(node, visit);
      };
      visit(source.tree);
    }
    return payload.insert("findings", findings);
  }
}
