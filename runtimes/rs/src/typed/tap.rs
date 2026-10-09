//! TypedTap — read-only observer of the typed payload.
//!
//! Taps must not mutate. Removing every Tap must yield identical output —
//! the manifesto invariant, preserved.

/// Observe a Ctx without mutating it. Errors are swallowed by the pipeline.
pub trait TypedTap<Ctx>: Send + Sync {
    fn observe(&self, ctx: &Ctx);

    fn name(&self) -> &str {
        std::any::type_name::<Self>()
    }
}
