/**
 * Valve: Conditional Flow Control
 *
 * A Valve wraps a Filter with a predicate — the inner filter only
 * executes when the predicate evaluates to true. Otherwise the payload
 * passes through unchanged.
 *
 * See also: Python, Rust, Go, C# implementations.
 */

import type { Payload, PayloadData } from "./payload.js";
import type { Filter } from "./filter.js";
import type { Predicate } from "./predicate.js";
import { predicateSymbol } from "./step_identity.js";

/**
 * Conditional flow control — gates a Filter with a predicate.
 *
 * Conforms to the Filter interface so it can be used anywhere a
 * Filter is expected.
 */
export class Valve<
  TIn extends PayloadData = PayloadData,
  TOut extends PayloadData = PayloadData,
> implements Filter<TIn, TOut>
{
  /** The predicate's identity (extra detail; the Valve is identified by its inner filter). */
  readonly predicateSymbol: string;
  private readonly _inner: Filter<TIn, TOut>;
  private readonly _predicate: Predicate<TIn>;
  /** Whether the last call was skipped. Used by Pipeline for state tracking. */
  _lastSkipped = false;

  constructor(
    inner: Filter<TIn, TOut>,
    predicate: Predicate<TIn>,
  ) {
    // A predicate object (conformance/API.md, "Valve"), identified by its class.
    this.predicateSymbol = predicateSymbol(predicate);
    this._inner = inner;
    this._predicate = predicate;
  }

  call(payload: Payload<TIn>): Payload<TOut> | Promise<Payload<TOut>> {
    if (this._predicate.test(payload)) {
      this._lastSkipped = false;
      return this._inner.call(payload);
    }
    this._lastSkipped = true;
    return payload as unknown as Payload<TOut>;
  }

  toString(): string {
    return `Valve(${this._inner.constructor.name}, ${this.predicateSymbol})`;
  }
}
