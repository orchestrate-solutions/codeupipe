//! codeupipe-core — Rust runtime
//!
//! The 8 core CUP primitives for WASM, desktop, and embedded pipelines.
//! Zero external dependencies. WASM-compatible.
//!
//! All runtimes (Python, TypeScript, Rust, Go, C#) share the same
//! mental model and API shape.

mod filter;
mod hook;
mod nestable;
mod parallel;
mod payload;
mod pipeline;
mod predicate;
mod state;
mod step_identity;
mod stream_filter;
mod tap;
mod valve;
pub mod typed;

#[cfg(feature = "wasm")]
mod wasm;

pub use filter::Filter;
pub use nestable::Nestable;
pub use parallel::Parallel;
pub use predicate::Predicate;
pub use hook::Hook;
pub use payload::{MutablePayload, Payload, Value};
pub use pipeline::Pipeline;
pub use state::State;
pub use stream_filter::StreamFilter;
pub use tap::Tap;
pub use valve::Valve;
