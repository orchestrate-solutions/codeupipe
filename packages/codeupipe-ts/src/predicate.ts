import type { Payload } from "./payload.ts";

/**
 * Predicate: asks a yes-or-no question about the data.
 *
 * A Predicate is an object. Its settings (a threshold, a flag) are on the
 * instance. It reads the Payload and does not write to it.
 */
export interface Predicate {
  test(payload: Payload): boolean;
}
