//! Predicate: a Valve's condition (conformance/API.md, "Valve").
//!
//! An object: a named type implementing `Predicate`, identified by its type
//! path like a step, with any configuration in its fields. There is no impl
//! for functions or closures, so passing one to `Valve::new` does not
//! compile.

use crate::payload::Payload;

pub trait Predicate: Send + Sync {
    fn test(&self, payload: &Payload) -> bool;
}
