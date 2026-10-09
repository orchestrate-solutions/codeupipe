/**
 * Filter: The Processing Unit
 *
 * The Filter interface defines the contract for payload processors.
 * Each Filter takes a Payload in, processes it, and returns a
 * (potentially transformed) Payload out.
 *
 * See also: Python, Rust, Go, C# implementations.
 */

import type { Payload, PayloadData } from "./payload.js";

/**
 * Processing unit — takes a payload in, returns a transformed payload out.
 * All filters are async (Promise-based).
 */
export interface Filter<
  TIn extends PayloadData = PayloadData,
  TOut extends PayloadData = PayloadData,
> {
  /** Sync (for `run`) or async (only under `runAsync`). */
  call(payload: Payload<TIn>): Payload<TOut> | Promise<Payload<TOut>>;
}
