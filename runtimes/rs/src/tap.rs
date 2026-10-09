//! Tap: Observation Point
//!
//! A Tap is a non-modifying observation point in the pipeline.
//! It receives the payload for inspection but never modifies it.
//!
//! See also: TypeScript, Python, Go, C# implementations.

use crate::payload::Payload;

/// Non-modifying observation point — inspect the payload without changing it.
pub trait Tap: Send + Sync {
    /// Observe the payload. Must not modify it.
    fn observe(&self, payload: &Payload);
}
