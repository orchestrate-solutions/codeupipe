//! TypedFilter — the typed processing unit.
//!
//! Same contract as Filter, but the payload IS your Ctx type. No HashMap.
//! The pipeline holds `Box<dyn TypedFilter<Ctx>>` so a chain can be
//! composed from heterogeneous concrete filters at runtime.

use super::TypedError;

/// A payload processor over a typed context `Ctx`.
///
/// `Ctx` should be owned and Send + Sync so it can flow through
/// concurrent pipelines. `Clone` is not required; filters receive
/// ownership and return ownership.
pub trait TypedFilter<Ctx>: Send + Sync {
    fn call(&self, ctx: Ctx) -> Result<Ctx, TypedError>;

    fn name(&self) -> &str {
        std::any::type_name::<Self>()
    }

    /// Whether the last `call` skipped its work (see `Filter::last_skipped`).
    fn last_skipped(&self) -> bool {
        false
    }
}
