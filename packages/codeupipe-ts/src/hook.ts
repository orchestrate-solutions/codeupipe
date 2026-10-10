import type { Payload } from "./payload.ts";

/**
 * Hook: sees the lifecycle of a run. Extend it and override what you need.
 *
 * `step` is the label of the step, or null for the pipeline itself. A Hook
 * reads the Payload and does not write to it. Its methods can be async.
 */
export class Hook {
  /** Before a step, or before the pipeline starts (`step` is null). */
  before(step: string | null, payload: Payload): void | Promise<void> {}

  /** After a step, or after the pipeline ends (`step` is null). */
  after(step: string | null, payload: Payload): void | Promise<void> {}

  /** When a Filter fails: for the step, then for the pipeline (`step` is null). */
  onError(step: string | null, error: unknown, payload: Payload): void | Promise<void> {}
}
