//! Nestable: a named pipeline type that can be nested as one step.
//!
//! The Rust equivalent of a Pipeline subclass: a named type wrapping a
//! Pipeline, identified by its type path like a filter (conformance/API.md,
//! "Step identity"). `Pipeline` itself does not implement it, so nesting a
//! plain, unnamed pipeline is a compile error.
//!
//! ```ignore
//! struct Onboarding(Pipeline);
//! impl Nestable for Onboarding {
//!     fn into_pipeline(self) -> Pipeline { self.0 }
//! }
//! ```

use crate::pipeline::Pipeline;

pub trait Nestable: 'static {
    fn into_pipeline(self) -> Pipeline;
}
