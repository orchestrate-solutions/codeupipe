/**
 * Hook: The Enhancement Layer
 *
 * Lifecycle hooks for pipeline execution. Implementations can
 * override any combination of before(), after(), and onError().
 *
 * See also: Python, Rust, Go, C# implementations.
 */

import type { Payload, PayloadData } from "./payload.js";

/**
 * Lifecycle hook for pipeline execution.
 * All methods are optional — override what you need.
 */
export interface Hook<T extends PayloadData = PayloadData> {
  before?(
    step: string | null,
    payload: Payload<T>,
  ): Promise<void> | void;

  after?(
    step: string | null,
    payload: Payload<T>,
  ): Promise<void> | void;

  onError?(
    step: string | null,
    error: Error,
    payload: Payload<T>,
  ): Promise<void> | void;
}
