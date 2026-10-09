/**
 * TypedTap — read-only observer of a typed payload.
 *
 * Taps must not mutate ctx. Removing every Tap must yield identical
 * pipeline output — the manifesto invariant.
 */
export interface TypedTap<Ctx> {
  observe(ctx: Ctx): Promise<void> | void;
  readonly name?: string;
}
