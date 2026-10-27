use crate::payload::Payload;

/// Predicate: asks a yes-or-no question about the data.
///
/// A Predicate is a type. Its settings (a threshold, a flag) are on the
/// instance. It reads the Payload and does not write to it.
pub trait Predicate {
    fn test(&self, payload: &Payload) -> bool;
}
