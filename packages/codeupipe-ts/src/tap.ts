import type { Payload } from "./payload.ts";

/**
 * Tap: reads the data as it goes by. It does not write to the Payload.
 * A Tap failure is recorded in State and never stops the run.
 */
export interface Tap<P = Payload> {
  observe(payload: P): void | Promise<void>;
}
