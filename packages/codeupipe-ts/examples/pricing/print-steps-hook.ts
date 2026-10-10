import { Hook } from "../../src/index.ts";

/**
 * A Hook: sees the lifecycle. `step` is the label of the step, which is the
 * name of its class. It is null for the pipeline itself.
 */
export class PrintStepsHook extends Hook {
  override before(step: string | null): void {
    if (step !== null) {
      console.log("  " + step);
    }
  }
}
