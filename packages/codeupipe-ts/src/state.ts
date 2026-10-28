/**
 * State: what happened in the last run.
 *
 * Which steps executed, which a Valve skipped, the errors, and the timings
 * when timing is on. Read it after a run through `pipeline.state`.
 */
export class State {
  /** Step labels, in order. */
  readonly executed: string[] = [];
  /** Steps that a Valve did not run. */
  readonly skipped: string[] = [];
  /** Pairs of label and error. */
  readonly errors: Array<[string, unknown]> = [];
  /** Label to seconds, when timing is on. */
  readonly timings: Map<string, number> = new Map();

  markExecuted(label: string): void {
    this.executed.push(label);
  }

  markSkipped(label: string): void {
    this.skipped.push(label);
  }

  recordTiming(label: string, seconds: number): void {
    this.timings.set(label, seconds);
  }

  recordError(label: string, error: unknown): void {
    this.errors.push([label, error]);
  }
}
