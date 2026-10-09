//! Filter: The Processing Unit
//!
//! The Filter trait defines the contract for payload processors.
//! Each Filter takes a Payload in, processes it, and returns a
//! (potentially transformed) Payload out.
//!
//! See also: TypeScript, Python, Go, C# implementations.

use crate::payload::Payload;

/// Processing unit — takes a payload in, returns a transformed payload out.
pub trait Filter: Send + Sync {
    /// Process the payload and return a transformed result.
    fn call(&self, payload: Payload) -> Result<Payload, Box<dyn std::error::Error + Send + Sync>>;

    /// Whether the last `call` skipped its work (a closed Valve). The
    /// Pipeline stores filters type-erased, so it asks rather than downcasts
    /// to record the step in `state.skipped` instead of `state.executed`.
    fn last_skipped(&self) -> bool {
        false
    }
}
