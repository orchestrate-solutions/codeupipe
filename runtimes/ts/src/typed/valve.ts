/**
 * TypedValve — conditional gate wrapping a TypedFilter.
 *
 * Runs the wrapped filter only when the predicate returns true.
 * Skipped runs pass ctx through unchanged and record 'skipped' in State.
 */
import type { TypedFilter } from "./filter.js";

export class TypedValve<Ctx> implements TypedFilter<Ctx> {
  readonly name: string;
  private _lastSkipped = false;

  constructor(
    private readonly inner: TypedFilter<Ctx>,
    private readonly predicate: (ctx: Ctx) => boolean,
    name?: string,
  ) {
    this.name = name ?? `TypedValve(${inner.name ?? "anon"})`;
  }

  async call(ctx: Ctx): Promise<Ctx> {
    if (this.predicate(ctx)) {
      this._lastSkipped = false;
      return this.inner.call(ctx);
    }
    this._lastSkipped = true;
    return ctx;
  }

  get lastSkipped(): boolean {
    return this._lastSkipped;
  }
}
