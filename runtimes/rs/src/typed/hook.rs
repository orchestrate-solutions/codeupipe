//! TypedHook — lifecycle callback for the typed pipeline.
//!
//! Fires on before/after for each step and the pipeline itself, and on
//! error at any step. `step_name` is None for pipeline-level events.
//!
//! Design note on `on_error`: filters consume Ctx by value. When a filter
//! errors, ctx has already been moved into the failing call — there is no
//! valid ctx to hand back. If you need ctx-on-error, place a TypedTap
//! immediately upstream and snapshot ctx there. This preserves the
//! manifesto invariant that hooks are lifecycle, not state.

/// Lifecycle callback attached to a TypedPipeline.
pub trait TypedHook<Ctx>: Send + Sync {
    fn before(&self, _step_name: Option<&str>, _ctx: &Ctx) {}
    fn after(&self, _step_name: Option<&str>, _ctx: &Ctx) {}
    fn on_error(&self, _step_name: Option<&str>, _err: &str) {}
}
