import { basename } from "node:path";

import type { Filter, Payload } from "codeupipe";
import ts from "typescript";

import { CompileRefusal } from "./compile-refusal.ts";
import { findClass, loadSource } from "./source-files.ts";
import type { ClassRef } from "./source-files.ts";
import type { Made, StepPlan } from "./step-plan.ts";

function extendsPipeline(node: ts.ClassDeclaration): boolean {
  return (node.heritageClauses ?? []).some((clause) => clause.token === ts.SyntaxKind.ExtendsKeyword
    && clause.types.some((type) => type.expression.getText() === "Pipeline"));
}

/**
 * Reads a pipeline class and lists its steps.
 *
 * The class extends `Pipeline`. Its constructor calls `super()` and then
 * only adds steps: `this.addFilter(new X(...))`, `this.addValve(new P(...),
 * new F(...))`, `this.addTap(new T(...))`, `this.addPipeline(new Inner())`.
 * A nested pipeline is flattened in place.
 *
 * Input keys: `file`, `className`.
 * Output keys: `steps` (a list of StepPlan).
 */
export class ResolvePipelineFilter implements Filter {
  call(payload: Payload): Payload {
    const file = payload.get<string>("file") ?? "";
    const className = payload.get<string>("className") ?? "";
    const pipeline = findClass(loadSource(file), className, `${basename(file)}:${className}`);
    return payload.insert("steps", this.stepsOf(pipeline, []));
  }

  private stepsOf(pipeline: ClassRef, outer: string[]): StepPlan[] {
    const where = pipeline.name;
    if (outer.includes(where)) {
      throw new CompileRefusal(where, "the pipeline is nested in itself", "Remove the cycle");
    }
    if (!extendsPipeline(pipeline.node)) {
      throw new CompileRefusal(where, "the class does not extend Pipeline", "Give the name of a class that extends Pipeline");
    }
    if (pipeline.node.members.some((member) => ts.isMethodDeclaration(member) && member.name.getText() === "run")) {
      throw new CompileRefusal(where, "the class has its own run", "Remove it: the compiler writes the run of Pipeline");
    }
    const made = (expression: ts.Expression | undefined, role: string): Made => {
      if (expression === undefined || !ts.isNewExpression(expression) || !ts.isIdentifier(expression.expression)) {
        throw new CompileRefusal(where, `the ${role} is not \`new ClassName(...)\``,
          "Make each step in the constructor of the pipeline, in the call that adds it");
      }
      const ref = findClass(pipeline.source, expression.expression.text, where);
      return { ref, args: expression.arguments ?? [], argSource: pipeline.source };
    };

    const steps: StepPlan[] = [];
    const constructor = pipeline.node.members.find(ts.isConstructorDeclaration);
    for (const statement of constructor?.body?.statements ?? []) {
      const call = ts.isExpressionStatement(statement) && ts.isCallExpression(statement.expression)
        ? statement.expression : undefined;
      if (call !== undefined && call.expression.kind === ts.SyntaxKind.SuperKeyword) continue;
      const method = call !== undefined && ts.isPropertyAccessExpression(call.expression)
        && call.expression.expression.kind === ts.SyntaxKind.ThisKeyword ? call.expression.name.text : undefined;
      if (call === undefined || method === undefined) {
        throw new CompileRefusal(where, `the constructor has a statement that does not add a step (\`${statement.getText().split("\n")[0]}\`)`,
          "Keep only super() and the calls that add steps");
      }
      if (method === "addFilter") {
        steps.push({ kind: "filter", filter: made(call.arguments[0], "Filter") });
      } else if (method === "addValve") {
        steps.push({ kind: "valve", predicate: made(call.arguments[0], "Predicate"), filter: made(call.arguments[1], "Filter") });
      } else if (method === "addTap") {
        steps.push({ kind: "tap", tap: made(call.arguments[0], "Tap") });
      } else if (method === "addPipeline") {
        const inner = made(call.arguments[0], "nested pipeline");
        if (inner.args.length > 0) {
          throw new CompileRefusal(where, `the nested pipeline \`${inner.ref.name}\` takes arguments`,
            "Give the nested pipeline no arguments");
        }
        steps.push(...this.stepsOf(inner.ref, [...outer, where]));
      } else if (method === "useHook") {
        throw new CompileRefusal(where, "the pipeline has a Hook",
          "The compiled code has no lifecycle. Remove the Hook, or run the pipeline itself");
      } else if (method === "observe") {
        throw new CompileRefusal(where, "the pipeline turns on timing or lineage",
          "The compiled code has no State. Remove the call, or run the pipeline itself");
      } else {
        throw new CompileRefusal(where, `the constructor calls \`this.${method}\``,
          "Keep only super() and the calls that add steps");
      }
    }
    return steps;
  }
}
