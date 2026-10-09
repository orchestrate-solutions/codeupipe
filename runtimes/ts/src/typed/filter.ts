/**
 * TypedFilter — the typed processing unit.
 *
 * Same contract as Filter, but the input/output IS your Ctx type.
 * All calls are async (Promise-based) for parity with the dynamic API.
 */
export interface TypedFilter<Ctx> {
  call(ctx: Ctx): Promise<Ctx>;
  readonly name?: string;
}
