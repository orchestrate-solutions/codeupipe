/**
 * TypedHook — lifecycle callback for the typed pipeline.
 *
 * Fires on before/after for each step and the pipeline itself, and on
 * error at any step. `stepName` is undefined for pipeline-level events.
 *
 * on_error receives err only. If you need ctx-on-error, place a
 * TypedTap immediately upstream and snapshot ctx there.
 */
export interface TypedHook<Ctx> {
  before?(stepName: string | undefined, ctx: Ctx): Promise<void> | void;
  after?(stepName: string | undefined, ctx: Ctx): Promise<void> | void;
  onError?(stepName: string | undefined, err: Error): Promise<void> | void;
}
