//! TypedValve — conditional gate for a typed pipeline.
//!
//! A Valve wraps a TypedFilter and a predicate. The wrapped filter only
//! runs when the predicate returns true. Skipped runs pass Ctx through
//! unchanged and mark the step as skipped in State.
//!
//! This is the manifesto's "elevate routing to Valve on the Pipeline" —
//! branching is statically inspectable because you can see the Valve in
//! the pipeline blueprint.

use super::{TypedError, TypedFilter};
use std::sync::atomic::{AtomicBool, Ordering};

/// A gated filter. Only runs when `predicate(&ctx)` is true.
pub struct TypedValve<Ctx> {
    inner: Box<dyn TypedFilter<Ctx>>,
    predicate: Box<dyn Fn(&Ctx) -> bool + Send + Sync>,
    last_skipped: AtomicBool,
}

impl<Ctx> TypedValve<Ctx> {
    pub fn new<F, P>(inner: F, predicate: P) -> Self
    where
        F: TypedFilter<Ctx> + 'static,
        P: Fn(&Ctx) -> bool + Send + Sync + 'static,
    {
        Self {
            inner: Box::new(inner),
            predicate: Box::new(predicate),
            last_skipped: AtomicBool::new(false),
        }
    }

    pub fn last_skipped(&self) -> bool {
        self.last_skipped.load(Ordering::Relaxed)
    }
}

impl<Ctx: Send + Sync> TypedFilter<Ctx> for TypedValve<Ctx> {
    fn call(&self, ctx: Ctx) -> Result<Ctx, TypedError> {
        if (self.predicate)(&ctx) {
            self.last_skipped.store(false, Ordering::Relaxed);
            self.inner.call(ctx)
        } else {
            self.last_skipped.store(true, Ordering::Relaxed);
            Ok(ctx)
        }
    }
}
