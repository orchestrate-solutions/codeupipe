//! Typed pipeline — compile-time schema, opt-in.
//!
//! `TypedPipeline<Ctx>` is a parallel API to `Pipeline`:
//! - same seven primitives (Filter, Tap, Valve, Hook, State, Payload, Pipeline)
//! - `Ctx` is your payload struct, known at compile time
//! - no `HashMap<String, Value>` — the payload IS the type
//!
//! Dynamic escape hatch: use `Ctx = HashMap<String, Value>` (or any owned
//! type) if you truly need a dynamic bag of keys. That path just falls back
//! to today's dynamic behavior.

mod filter;
mod hook;
mod pipeline;
mod tap;
mod valve;

pub use filter::TypedFilter;
pub use hook::TypedHook;
pub use pipeline::TypedPipeline;
pub use tap::TypedTap;
pub use valve::TypedValve;

/// Error alias used by the typed API.
pub type TypedError = Box<dyn std::error::Error + Send + Sync>;
