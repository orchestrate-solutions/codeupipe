import type { Filter, Payload } from "codeupipe";

import { lowerClass, snakeCase } from "./lower-class.ts";
import type { LoweredStep, StepPlan } from "./step-plan.ts";

/**
 * Writes each step as a plain function.
 *
 * A function has the name `cup_<number>_<class name>`. The number is the
 * place of the step in the run, so two uses of one class have two names.
 *
 * Input keys: `steps`.
 * Output keys: `lowered` (a list of LoweredStep).
 */
export class LowerStepsFilter implements Filter {
  call(payload: Payload): Payload {
    const steps = payload.get<StepPlan[]>("steps") ?? [];
    const width = Math.max(2, String(steps.length).length);
    const lowered: LoweredStep[] = steps.map((step, index) => {
      const number = String(index + 1).padStart(width, "0");
      const name = (prefix: string, className: string) => `cup_${number}_${prefix}${snakeCase(className)}`;
      if (step.kind === "filter") {
        return { kind: "filter", filter: lowerClass(step.filter, "Filter", name("", step.filter.ref.name)) };
      }
      if (step.kind === "tap") {
        return { kind: "tap", tap: lowerClass(step.tap, "Tap", name("", step.tap.ref.name)) };
      }
      return {
        kind: "valve",
        predicate: lowerClass(step.predicate, "Predicate", name("when_", step.predicate.ref.name)),
        filter: lowerClass(step.filter, "Filter", name("", step.filter.ref.name)),
      };
    });
    return payload.insert("lowered", lowered);
  }
}
